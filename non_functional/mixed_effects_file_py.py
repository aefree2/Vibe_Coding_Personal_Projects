#AAAAAA

import pandas as pd
import statsmodels.api as sm
import scipy.stats as stats
import statsmodels.formula.api as smf
import numpy as np
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
from ast import literal_eval
import re
from mixed_effects_class import make_mask, cliffs_delta
import json

# imports, classes imported, functions imported, classes defined, 
# functions defined, (async fn defined), block comments, line comments, 
# all calls functions called, classes called, imports used

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


def run_metric_tests(
    df,
    group_col="source",
    group_a="SideProject",
    group_b="Vibecoding",
    exclude_cols=None,
):
    if exclude_cols is None:
        exclude_cols = {
            "url", "url_x", "commit", "proj_name",
            "file_path", "file_name", "fn_name", "fn_sig",
            "fn_code", "origin_class"
        }

    results = []

    # Convert booleans to 0/1
    test_df = df.copy()
    bool_cols = test_df.select_dtypes(include="bool").columns
    test_df[bool_cols] = test_df[bool_cols].astype(int)

    candidate_cols = [
        col for col in test_df.columns
        if col not in exclude_cols
        and col != group_col
        and pd.api.types.is_numeric_dtype(test_df[col])
    ]

    for col in candidate_cols:
        a = test_df.loc[test_df[group_col] == group_a, col].dropna()
        b = test_df.loc[test_df[group_col] == group_b, col].dropna()

        if len(a) == 0 or len(b) == 0:
            continue

        # Skip columns with no variation
        if a.nunique() <= 1 and b.nunique() <= 1:
            continue

        if (col == "avg_lines_in_comment"):
            a = a[a!=0]
            b = b[b!=0]

        stat, p = mannwhitneyu(a, b, alternative="two-sided")
        delta = cliffs_delta(b,a)
        print(col)

        results.append({
            "metric": col,
            f"{group_a}_n": len(a),
            f"{group_b}_n": len(b),
            f"{group_a}_median": a.median(),
            f"{group_b}_median": b.median(),
            f"{group_a}_mean": a.mean(),
            f"{group_b}_mean": b.mean(),
            "effect_size_median_diff": b.median() - a.median(),
            "u_stat": stat,
            "effect_direction":
            "Vibecoding > SideProject"
            if delta>0
            else "SideProject > Vibecoding",
            "size": delta,
            "p_value": p,
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df["p_adj_bh"] = multipletests(
            results_df["p_value"],
            method="fdr_bh"
        )[1]

        results_df = results_df.sort_values("p_adj_bh")

    return results_df

def div_by_zero(df, num_col, div_col):
    return np.divide(
        df[num_col],
        df[div_col],
        out = np.full(len(df), np.nan),
        where=df[div_col] != 0,
    )

def fast_literal_eval(series):
    unique = series.dropna().unique()
    lookup = {s: literal_eval(s) for s in unique}
    return series.map(lookup)


if __name__ == "__main__":
    df = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]

    df_py = df[df.extn == "py"]

    py_vc = make_mask(source, df_py, names[0])
    py_sp = make_mask(source, df_py, names[1])

    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    df_all = pd.concat([py_sp, py_vc], ignore_index=True)
    df_all

    #Functions Defined, Async functions defined

    # fn_df = pd.read_csv("../dataset_features/all_fn.csv")
    fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])

    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'line_count', 'line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    fn_df.drop_duplicates(inplace=True)
    print(fn_df.columns)

    func_stats = (
    fn_df.groupby(["url", "file_path"])
    .agg(
        n_functions=("url", "size"),
        n_async_functions=('is_aysnc', "sum")
    )
    .reset_index())
    
    f_merged = pd.merge(df_all, func_stats, how="left", on="file_path")
    f_merged.drop("url_y", inplace=True,axis=1)
    f_merged.fillna(0.0, inplace=True)

    #Classes Defined
    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)
    class_stats = (class_df.groupby(["url","file_path"]).agg(class_count=("file_path", "size"))).reset_index()
    
    c_f_merged = pd.merge(f_merged, class_stats, how= "left", on="file_path")
    c_f_merged.drop("url", inplace=True,axis=1)
    c_f_merged.fillna(0,inplace = True)

    # block comments, line comments,
    # colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw"] 
    # comments = pd.read_csv("../dataset_features/comments_r.csv", names=colnames, header=None)
    comments=pd.read_csv("../dataset_features/comments_revised.csv")
    comments.drop_duplicates(inplace=True)

    comments[["comment_kind", "comment_n_lines"]] = (
    comments.apply(comment_stats, axis=1)
    )

    comment_summary = (
    comments.groupby(["url", "file_path", "comment_kind"])
      .agg(
            n_comments=("raw", "size"),
            n_comment_lines=("comment_n_lines", "sum"),
            n_at_end_of_code_line=("at_end_of_code_line", "sum"),
            n_blank_in_docstring=("blank_in_docstring", "sum")
      )
      .reset_index()
)

    comment_summary = comment_summary.pivot_table(
        index="file_path",
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

    c_c_f_merged = pd.merge(c_f_merged, comment_summary, how= "left", on="file_path")
    # c_c_f_merged.drop("url", inplace=True,axis=1)
    c_c_f_merged.fillna(0,inplace = True)

    # Imports
    df_imports = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df_imports.drop_duplicates(inplace=True)
    df_imports["imports"] = df_imports["imports"].apply(literal_eval)

    project_imports = (
    df_imports.groupby(["url", "file_path"])["imports"]
      .agg(
          n_imports=lambda x: sum(len(i) for i in x),
      )
      .reset_index()
)

    # print(project_imports.head())
    i_c_c_f_merged = pd.merge(c_c_f_merged, project_imports, how= "left", on="file_path")
    i_c_c_f_merged.drop("url", inplace=True,axis=1)
    i_c_c_f_merged.fillna(0,inplace = True)

    # All Functions Imported
    df_fn_imports = pd.read_csv("fn_level_metrics.csv")
    # print(df_fn_imports.import_locations.isna().sum())
    # print(df_fn_imports.import_locations)
    df_fn_imports = df_fn_imports.fillna({'import_locations':"[]",'called_in_files':"[]"})
    df_fn_imports = df_fn_imports.filter(items=["url", "file_path", "import_locations", "called_in_files"])
    # print(df_fn_imports.import_locations)
    # print(df_fn_imports.import_locations.isna().sum())
    # df_fn_imports["called_in_files"].fillna("[\"NONE\"]", inplace=True)
    print("starting literal evals")
    # df_fn_imports["import_locations"] = df_fn_imports["import_locations"].apply(literal_eval)
    # df_fn_imports["called_in_files"] = df_fn_imports["called_in_files"].apply(literal_eval)
    # df_fn_imports["import_locations"] = df_fn_imports["import_locations"].map(json.loads)
    # df_fn_imports["called_in_files"] = df_fn_imports["called_in_files"].map(json.loads)

    df_fn_imports["import_locations"] = fast_literal_eval(
        df_fn_imports["import_locations"]
    )

    df_fn_imports["called_in_files"] = fast_literal_eval(
        df_fn_imports["called_in_files"]
    )
    # print(df_fn_imports.import_locations)
    print("beginning explode")
    fn_imports = (
        df_fn_imports
        .explode("import_locations")
        .rename(columns={"import_locations": "import_target"})
        .groupby(["url", "import_target"])
        .size()
        .reset_index(name="n_fn_imports")
        .rename(columns={"import_target": "file_path"})
    )
    print("fn_imports")
    print(fn_imports.head())
    print(fn_imports.columns)

    if "url_x" in i_c_c_f_merged.columns:
        i_c_c_f_merged = i_c_c_f_merged.rename(columns={"url_x": "url"})

    # Count within-project imports by file, not by the file that defined the symbol.
    i_c_c_f_merged = i_c_c_f_merged.merge(
        fn_imports,
        how="left",
        on=["url", "file_path"],
    )
    i_c_c_f_merged["n_fn_imports"] = i_c_c_f_merged["n_fn_imports"].fillna(0)
    print(i_c_c_f_merged.columns)

    # All classes imported
    df_class_imports = pd.read_csv("class_level_metrics.csv")
    df_class_imports = df_class_imports.fillna({'import_locations':"[\'None\']",'called_in_files':"[\'None\']"})
    df_class_imports["import_locations"] = df_class_imports["import_locations"].apply(literal_eval)
    df_class_imports["called_in_files"] = df_class_imports["called_in_files"].apply(literal_eval)
    # print(df_class_imports.columns)
    class_imports = (
        df_class_imports
        .explode("import_locations")
        .rename(columns={"import_locations": "import_target"})
        .groupby(["url", "import_target"])
        .size()
        .reset_index(name="n_class_imports")
        .rename(columns={"import_target": "file_path"})
    )
    print("class imports")
    print(class_imports.head())

    i_c_c_f_merged = i_c_c_f_merged.merge(
        class_imports,
        how="left",
        on=["url", "file_path"],
    )
    i_c_c_f_merged["n_class_imports"] = i_c_c_f_merged["n_class_imports"].fillna(0)

    # All Calls
    df_calls = pd.read_csv("../dataset_features/all_calls.csv", names= ["url", "commit", "project", "file_path", "file", "calls"])
    df_calls.drop_duplicates(inplace=True)

    df_calls["calls"] = df_calls["calls"].apply(literal_eval)
    project_calls = (
    df_calls.groupby(["url", "file_path"])["calls"]
      .agg(
          n_calls=lambda x: sum(len(i) for i in x),
      )
      .reset_index()
    )

    # print(project_calls.head())
    if "url_x" in i_c_c_f_merged.columns:
        i_c_c_f_merged = i_c_c_f_merged.rename(columns={"url_x": "url"})
    calls_merged =  i_c_c_f_merged.merge(project_calls, how="left", on=["url", "file_path"])
    # print(calls_merged.columns)

    #Function Calls (TO DO)
    print(df_fn_imports.columns)
    fn_calls_long = df_fn_imports.explode("called_in_files")
    # print(fn_calls_long.head())
    fn_calls = fn_calls_long.groupby(["url", "called_in_files"]).agg(
            n_unique_fn_calls=("called_in_files", "size"),
        )
    print(fn_calls.head())
    calls_merged =  calls_merged.merge(fn_calls, how="left", left_on=["url", "file_path"], right_on=["url", "called_in_files"])
    print(calls_merged.columns)
    

    #Classes Called (TO DO)
    class_calls_long = df_class_imports.explode("called_in_files")
    print(class_calls_long.columns)
    class_calls = class_calls_long.groupby(["url", "called_in_files"]).agg(
            n_unique_class_calls=("called_in_files", "size"),
        )
    print(class_imports.head())
    print(class_calls.columns)
    calls_merged =  calls_merged.merge(class_calls, how="left", left_on=["url", "file_path"], right_on=["url", "called_in_files"])
    print(calls_merged.columns)

    calls_merged["n_comment_lines_block"] = calls_merged["n_comment_lines_block"] - calls_merged["n_blank_in_docstring_block"]
    calls_merged["n_comments_lines"] = calls_merged["n_comment_lines_line"] + calls_merged["n_comment_lines_block"]
    calls_merged["n_comments"] = calls_merged["n_comments_line"] + calls_merged["n_comments_block"]


    calls_merged["avg_lines_in_comment"] = div_by_zero(calls_merged, "n_comments_lines", "n_comments")

    print("Average lines in comment")
    print(calls_merged["avg_lines_in_comment"])
    print()
    


    # STATS

    #Normalize everyting around number of lines:

    calls_merged["n_code_lines"] = calls_merged["n_lines"] - calls_merged["blank_lines"] - calls_merged["n_comment_lines_block"] - calls_merged["n_comment_lines_line"] + calls_merged["n_at_end_of_code_line_line"]
    # calls_merged["n_lines"] = calls_merged["n_code_lines"] +
    calls_merged["n_external_fn_calls"] = (calls_merged["n_calls"] - calls_merged["n_unique_fn_calls"])

    calls_merged["n_external_fn_calls_by_code"] = div_by_zero(
        calls_merged,
        "n_external_fn_calls",
        "n_code_lines",
    )

    calls_merged["n_external_imports"] = (calls_merged["n_imports"] - calls_merged["n_fn_imports"] - calls_merged["n_class_imports"])
    calls_merged["n_internal_imports"] = (calls_merged["n_fn_imports"] + calls_merged["n_class_imports"])

    calls_merged["n_external_imports_by_code"] = div_by_zero(
    calls_merged,
    "n_external_imports",
    "n_code_lines",
    )


    calls_merged["blank_by_code"] = div_by_zero(calls_merged, "blank_lines", "n_code_lines")
    calls_merged["percent_comments"] = div_by_zero(calls_merged, "n_comments_lines", "n_lines")
    calls_merged["char_by_code"] = div_by_zero(calls_merged, "char", "n_code_lines")
    calls_merged["n_functions_by_code"] = div_by_zero(calls_merged, "n_functions", "n_code_lines")
    calls_merged["n_async_functions_by_code"] = div_by_zero(calls_merged, "n_async_functions", "n_code_lines")
    calls_merged["class_count_by_code"] = div_by_zero(calls_merged, "class_count", "n_code_lines")
    calls_merged["n_comment_lines_block_by_code"] = div_by_zero(calls_merged, "n_comment_lines_block", "n_code_lines")
    calls_merged["n_comment_lines_line_by_code"] = div_by_zero(calls_merged, "n_comment_lines_line", "n_code_lines")
    calls_merged["n_imports_by_code"] = div_by_zero(calls_merged, "n_imports", "n_code_lines")
    calls_merged["n_calls_by_code"] = div_by_zero(calls_merged, "n_calls", "n_code_lines")
    calls_merged["n_comments_block_by_code"] = div_by_zero(calls_merged, "n_comments_block", "n_code_lines")
    calls_merged["n_comments_line_by_code"] = div_by_zero(calls_merged, "n_comments_line", "n_code_lines")
    calls_merged["avg_len_block_comment"] = div_by_zero(calls_merged, "n_comment_lines_block", "n_comments_block")
    calls_merged["avg_len_line_comment"] = div_by_zero(calls_merged, "n_comment_lines_line", "n_comments_line")
    calls_merged["n_lines_by_code"] = div_by_zero(calls_merged, "n_lines", "n_code_lines")
    calls_merged["n_fn_called_by_code"] = div_by_zero(calls_merged, "n_unique_fn_calls", "n_code_lines")
    calls_merged["n_class_called_by_code"] = div_by_zero(calls_merged, "n_unique_class_calls", "n_code_lines")
    calls_merged["n_fn_imports_by_code"] = div_by_zero(calls_merged, "n_fn_imports", "n_code_lines")
    calls_merged["n_class_imports_by_code"] = div_by_zero(calls_merged, "n_class_imports", "n_code_lines")

    calls_merged["percent_code"] = div_by_zero(calls_merged, "n_code_lines", "n_lines")
    calls_merged["percent_blank"] = div_by_zero(calls_merged, "blank_lines", "n_lines")


    
    calls_merged.to_csv("file_level_py_raw.csv")
    stats_results = run_metric_tests(
    calls_merged,
    group_col="source",
    group_a="SideProject",
    group_b="Vibecoding"
)
    stats_results= stats_results.sort_values("p_adj_bh")

    stats_results.to_csv("file_level_py.csv")
