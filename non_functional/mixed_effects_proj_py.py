### 
import pandas as pd
import statsmodels.api as sm
import scipy.stats as stats
import statsmodels.formula.api as smf
import numpy as np
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
import re
from mixed_effects_class import cliffs_delta, make_mask
import json
from ast import literal_eval
from mixed_effects_proj import run_stats_tests




def read_concatenated_json_arrays(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    decoder = json.JSONDecoder()
    idx = 0
    objects = []

    project_num = 0

    while idx < len(text):
        # Skip whitespace/newlines between JSON objects
        while idx < len(text) and text[idx].isspace():
            idx += 1

        if idx >= len(text):
            break

        obj, end = decoder.raw_decode(text, idx)

        # obj is one project's list of pylint messages
        for entry in obj:
            entry["project_num"] = project_num
            objects.append(entry)

        project_num += 1
        idx = end

    return objects

def comment_stats(row):
    raw = str(row["raw"])

    return pd.Series({
        "comment_kind": (
            "line"
            if row["type"] == "comment"
            else "block"
        ),
        "comment_n_lines": len(raw.splitlines())
    })


def add_project_names_by_majority_match(
    pylint_df,
    projects_df,
    pylint_path_col="path",
    project_path_col="file_path",
    project_col="url",
    project_num_col="project_num",
):
    # print(pylint_df.iloc[0])
    # print(projects_df.head())
    matches = pylint_df.merge(
        projects_df[[project_col, project_path_col]],
        left_on=pylint_path_col,
        right_on=project_path_col,
        how="inner"
    )
    # print("matches")
    # print(matches)

    project_map = (
        matches
        .groupby([project_num_col, project_col])
        .size()
        .reset_index(name="n_matching_paths")
        .sort_values([project_num_col, "n_matching_paths"], ascending=[True, False])
        .drop_duplicates(project_num_col)
    )

    result = pylint_df.merge(
        project_map[[project_num_col, project_col]],
        on=project_num_col,
        how="left"
    )

    return result, project_map

if __name__ == "__main__":
    # total imports, unique imports, classes, functions, async functions, comments
    #Pylint warnings
    df = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    df.drop_duplicates(subset=["file_path"], inplace=True)
    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]

    py_vc = make_mask(source, df, names[0])
    py_sp = make_mask(source, df, names[1])

    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    df_all = pd.concat([py_sp, py_vc], ignore_index=True)
    
    #cleaning files to remove the .git folder

    df_all_all = df_all[~df_all["file_path"].str.contains("/.git/")]

    #adding in the files that couldn't be read
    df_failed = pd.read_csv("../dataset_features/clone_failures.csv", names=["url", "proj_name", "file_path", "reason"])
    df_failed = df_failed.drop_duplicates(subset=["file_path"], keep="last")
    # df_failed.drop_duplicates(inplace=True)
    # print(df_failed.head())


    py_vc = make_mask(source, df_failed, names[0])
    py_sp = make_mask(source, df_failed, names[1])

    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"
    df_failed_all = pd.concat([py_sp, py_vc], ignore_index=True)
    df_failed_all = df_failed_all[~df_failed_all["file_path"].str.contains("/.git/")]

    df_merged_all = pd.concat([df_failed_all, df_all_all], join='outer', axis=0, ignore_index=True)
    print(df_merged_all.groupby("source")["url"].nunique())
    # print(df_merged_all.size) 
    # df_merged_all.drop("reason")
    df_merged_all = df_merged_all[df_merged_all["extn"] == "py"]
    df_all_py = df_merged_all.groupby(["url", "source"]).agg(
        n_files = ("url", "size"),
        n_lines =("n_lines", "sum"),
        n_chars = ("char", "sum"),
        n_blank_lines = ("blank_lines", "sum")
    ).reset_index()
    # print(df_all_py.head())
    print(df_all_py.groupby("source")["url"].nunique())

    #Get out of here the number of files and the number of lines
    
    #Imports


    df = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df["imports"] = df["imports"].apply(literal_eval)

    project_imports = (
    df.groupby(["url"])["imports"]
      .agg(
          n_imports=lambda x: sum(len(i) for i in x),
          n_unique_imports=lambda x: len(set().union(*x)) if len(x) else 0
      )
      .reset_index()
    )

    imp_merged = df_all_py.merge(project_imports, on=["url"], how="left")
    print(imp_merged.groupby("source")["url"].nunique())

    # Number of functions
    fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])

    # fn_df.drop_duplicates(subset=["file_path"], inplace=True)

    func_stats = (
    fn_df.groupby("url")
    .agg(
        n_functions=("url", "size"),
        n_async_functions=("is_aysnc", "sum")
    )
    .reset_index())

    merged = imp_merged.merge(
    func_stats,
    on=["url"],
    how="left"
    )
    # print(merged.head())
    print(merged.groupby("source")["url"].nunique())

    #Number of classes
    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)

    func_stats = (class_df.groupby("url").agg(class_count=("url", "size"))).reset_index()

    merged_next = merged.merge(
    func_stats,
    on=["url"],
    how="left"
    ).fillna(0)
    # print(merged_next.head())
    print(merged_next.groupby("source")["url"].nunique())

    #Number of comments
    # colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw"] 
    # comments = pd.read_csv("../dataset_features/comments.csv", names=colnames, header=None)
    comments=pd.read_csv("../dataset_features/comments_revised.csv")
    comments.drop_duplicates(inplace=True)
    # print(comments.head())


    comments[["comment_kind", "comment_n_lines"]] = (
    comments.apply(comment_stats, axis=1)
    )

    comment_summary = (
    comments.groupby(["url", "comment_kind"])
      .agg(
          n_comments=("raw", "size"),
          n_comment_lines=("comment_n_lines", "sum"),
          n_at_end_of_code_line=("at_end_of_code_line", "sum"),
          n_blank_in_docstring=("blank_in_docstring", "sum")
      )
      .reset_index()
)

    comment_summary = comment_summary.pivot_table(
        index="url",
        columns="comment_kind",
        values=[
            "n_comments",
            "n_comment_lines",
            "n_at_end_of_code_line",
            "n_blank_in_docstring"
        ],
        fill_value=0
    )

    comment_summary.columns = [
        f"{metric}_{kind}"
        for metric, kind in comment_summary.columns
    ]

    comment_summary = comment_summary.reset_index()

    total_merged = merged_next.merge(comment_summary, how="left", on="url")
    print(total_merged.groupby("source")["url"].nunique())
    # print(total_merged.head())

    #Local Imports
    #Function imports

    df_fn_imports = pd.read_csv("fn_level_metrics.csv")
    # print(df_fn_imports.columns)

    fn_imports = df_fn_imports.groupby(["url"]).agg(
            n_fn_imports=("n_times_imported", "sum"),
            n_fn_called=('n_total_calls', "sum")


        )
    # print(fn_imports.head())

    tt_merged = total_merged.merge(fn_imports, on=["url"], how="left")
    # print(tt_merged)
    print(tt_merged.groupby("source")["url"].nunique())

    #Getting all the calls
    df_all_calls = pd.read_csv(
    "../dataset_features/all_calls.csv", names=["url", "commit", "project", "file_path", "file", "calls"])
    df_all_calls.drop_duplicates(inplace=True)
    df_all_calls["calls"] = df_all_calls["calls"].apply(literal_eval)

    # total calls per project
    total_calls = (
        df_all_calls
        .explode("calls")
        .rename(columns={"calls": "called_fn"})
        .groupby("url")
        .agg(n_total_calls=("called_fn", "size"))
        .reset_index()
    )

    tt_merged = tt_merged.merge(total_calls, on="url", how="left")
    tt_merged["n_total_calls"] = tt_merged["n_total_calls"].fillna(0)

    tt_merged["n_out_of_project_calls"] = (
        tt_merged["n_total_calls"] - tt_merged["n_fn_called"])


    


    # PYLINT STUFF

    names = ["Vibecoding", "SideProject"]
    # print(df_merged_all.file_path.value_counts())
    df_merged_all["module_path"] = (
    df_merged_all["file_path"]
    .str.split("/")
    .str[1:]          # Remove the first path component
    .str.join("/")    # Rejoin the remaining components
    .str.replace("/", ".", regex=False)
)
    # print(df_merged_all.module_path.value_counts())


    entries = []

    arrays = read_concatenated_json_arrays("../dataset_features/pylint.json")
    pylint_entries = [
    item
    for arr in arrays
    for item in arr
    ]
    pylint_df = pd.DataFrame(arrays)
    # print(pylint_df.head())
    # print(pylint_df.columns)
    # print(len(pylint_df.module.unique()))
    # pylint_dupe_code = pylint_df[pylint_df["symbol"] == "duplicate-code"]
    pylint_df["module_path"] = pylint_df["module"] + "." + pylint_df["obj"] + "py"
    # print(pylint_dupe_code.message.iloc[0])



    # pylint = pd.read_json(, lines = True)
    # print(pylint.head())
    result, project_map = add_project_names_by_majority_match(pylint_df, df_merged_all)
    # print(result.iloc[0])
    url_error = (result.groupby(by=["url", "type"]).size()
    .reset_index(name="n_error")
    )
    # print(url_error.head())
    pylint_dupe_code = result[result["symbol"] == "duplicate-code"]
    df_wide = (
    url_error.pivot(
        index="url",
        columns="type",
        values="n_error"
    )
    .fillna(0)
    .reset_index()
    )
    # print(df_wide.head())
    # print(pylint_dupe_code.columns)
    pylint_dupe_code = pylint_dupe_code.groupby(by=["url"]).size().reset_index(name="n_duplications")
    # print(pylint_dupe_code.head())
    print("last tt_merged")
    print(tt_merged.groupby("source")["url"].nunique())

    pylint_merged = tt_merged.merge(df_wide, on=["url"], how="left")
    print("pylint merged")
    print(pylint_merged.groupby("source")["url"].nunique())
    duplicate_merged = pylint_merged.merge(pylint_dupe_code, on=["url"], how="left")
    print(duplicate_merged.groupby("source")["url"].nunique())
    # print(duplicate_merged.columns)
   
    duplicate_merged["n_comment_lines_block"] = duplicate_merged["n_comment_lines_block"] - duplicate_merged["n_blank_in_docstring_block"] #decided to put blank lines in blank lines not in the comment

    duplicate_merged["n_lines_py"] = duplicate_merged["n_lines"] - duplicate_merged["n_blank_lines"] - duplicate_merged["n_comment_lines_line"] - duplicate_merged["n_comment_lines_block"]  + duplicate_merged["n_at_end_of_code_line_line"]
    # print(duplicate_merged.columns)
    
    duplicate_merged["n_comments_lines"] = duplicate_merged["n_comment_lines_line"] + duplicate_merged["n_comment_lines_block"]
    duplicate_merged["n_comments"] = duplicate_merged['n_comments_line'] + duplicate_merged['n_comments_block']
    duplicate_merged.fillna({"n_comments":0},inplace=True)
    duplicate_merged.fillna({"n_comments_lines":0},inplace=True)

    duplicate_merged["avg_lines_in_comment"] = np.divide(
        duplicate_merged["n_comments_lines"],
        duplicate_merged["n_comments"],
        out = np.full(len(duplicate_merged), np.nan),
        where=duplicate_merged["n_comments"] != 0,
    ).replace([np.inf, -np.inf], np.nan)

    print(duplicate_merged["avg_lines_in_comment"].max())

    duplicate_merged["percent_comment_lines"] = np.divide(
        duplicate_merged["n_comments_lines"],
        duplicate_merged["n_lines"],
        out = np.full(len(duplicate_merged), np.nan),
        where=duplicate_merged["n_comments"] != 0,
    ).replace([np.inf, -np.inf], np.nan)



    
    #number of imports gets divided by number of files
    # duplicate_merged[cols] = np.divide(
    #     duplicate_merged[cols],
    #     duplicate_merged["n_lines"].to_numpy()[:, None],
    #     out=np.zeros_like(duplicate_merged[cols], dtype=float),
    #     where=duplicate_merged["n_lines"].to_numpy()[:, None] != 0,
    # )

    duplicate_merged["unique_imports_per_project"] = (
        duplicate_merged["n_unique_imports"]
        .div(duplicate_merged["n_files"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
    )

    duplicate_merged["imports_per_code_line"] = (
        duplicate_merged["n_imports"]
        .div(duplicate_merged["n_lines_py"], axis=0)
        .replace([np.inf, -np.inf], np.nan)

    )

    duplicate_merged["n_imports"] = (
        duplicate_merged["n_imports"]
        .div(duplicate_merged["n_files"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
    )

    duplicate_merged["avg_file_length"] = (
        duplicate_merged["n_lines_py"]
        .div(duplicate_merged["n_files"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
    )

    duplicate_merged["percent_blank_lines"] = (
        duplicate_merged["n_blank_lines"]
        .div(duplicate_merged["n_lines"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
    )

    duplicate_merged["percent_code_lines"] = (
            duplicate_merged["n_lines_py"]
            .div(duplicate_merged["n_lines"], axis=0)
            .replace([np.inf, -np.inf], np.nan)
        )

    exclude = ["url", "n_lines", "source", "n_imports", "n_lines_py", "n_files", 
               "avg_lines_in_comment", "avg_file_length", "n_imports", "percent_comment_lines", 
               "percent_blank_lines", "percent_code_lines", "unique_imports_per_project", "imports_per_code_line"]
    cols = duplicate_merged.columns.difference(exclude)
    # duplicate_merged.fillna(0)
    duplicate_merged[cols] = (
        duplicate_merged[cols]
        .div(duplicate_merged["n_lines_py"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
    )

    print(duplicate_merged.groupby("source")["url"].nunique())

    duplicate_merged.to_csv("proj_level_py.csv")

    results_df = run_stats_tests(duplicate_merged)

    results_df.to_csv("proj_level_results_py.csv")






