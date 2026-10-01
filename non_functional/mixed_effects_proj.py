import pandas as pd
import statsmodels.api as sm
import scipy.stats as stats
import statsmodels.formula.api as smf
import numpy as np
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
import re
from mixed_effects_class import cliffs_delta
from pathlib import PurePosixPath




def project_folder_stats(group):
    paths = group["file_path"].astype(str)

    folders = []
    depths = []

    for p in paths:
        path = PurePosixPath(p)
        # print(path)

        # folder containing the file
        folder = str(path.parent)

        folders.append(folder)

        # depth relative to project root
        depth = max(len(path.parent.parts) - 1, 0)
        # print(depths)
        depths.append(depth)

    unique_folders = set(folders)
    # print(unique_folders)

    return pd.Series({
        "n_folders": len(unique_folders),
        "max_folder_depth": max(depths, default=0),
        "avg_files_per_folder": len(paths) / max(len(unique_folders), 1)
    })

def run_tests(df_merged_all):
    df_sample= df_merged_all[ df_merged_all.url == "https://github.com/AJAYK-01/Anti-Nitro-Spam-Helper"]

    folder_statss = (
        df_sample.groupby(["url", "source"])
        .apply(project_folder_stats)
        .reset_index()
    )
    assert folder_statss["n_folders"].iloc[0] == 1
    assert folder_statss["max_folder_depth"].iloc[0] == 0

    df_sample= df_merged_all[ df_merged_all.url == "https://github.com/13pathak/AI-Popup-Infopedia"]

    folder_statss = (
        df_sample.groupby(["url", "source"])
        .apply(project_folder_stats)
        .reset_index()
    )
    # print(folder_statss)
    assert folder_statss["n_folders"].iloc[0] == 2
    assert folder_statss["max_folder_depth"].iloc[0] == 1

    df_sample= df_merged_all[ df_merged_all.url == "https://github.com/13pathak/AI-Popup-Infopedia"]

    folder_statss = (
        df_sample.groupby(["url", "source"])
        .apply(project_folder_stats)
        .reset_index()
    )
    assert folder_statss["n_folders"].iloc[0] == 2
    assert folder_statss["max_folder_depth"].iloc[0] == 1

    df_sample= df_merged_all[ df_merged_all.url == "https://github.com/1337hero/yeet"]

    folder_statss = (
        df_sample.groupby(["url", "source"])
        .apply(project_folder_stats)
        .reset_index()
    )
    #do we want to include .github folders? Those aren't hidden. I'm including them for now. 
    assert folder_statss["n_folders"].iloc[0] == 6
    assert folder_statss["max_folder_depth"].iloc[0] == 2

def run_metric_tests(df_merged):
    df_sample= df_merged[ df_merged.url == "https://github.com/AJAYK-01/Anti-Nitro-Spam-Helper"]

    # print(df_sample["n_files"])
    assert df_sample['n_files'].iloc[0] == 5
    # print("correct")


    df_sample= df_merged[ df_merged.url == "https://github.com/13pathak/AI-Popup-Infopedia"]

    # print(df_sample["n_files"])
    assert df_sample['n_files'].iloc[0] == 11
    # print("correct")



    df_sample= df_merged[ df_merged.url == "https://github.com/1337hero/yeet"]

    #do we want to include .github folders? Those aren't hidden. I'm including them for now. 
    assert df_sample['n_files'].iloc[0] == 25

def run_stats_tests(merged):
    

    exclude = [
        "url",
        "proj_name",
        "source"
    ]

    features = [
        c for c in merged.columns
        if c not in exclude
    ]

    results = []

    for col in features:

        # skip non-numeric columns
        if not pd.api.types.is_numeric_dtype(merged[col]):
            continue

        vibe = merged.loc[
            merged["source"] == "Vibecoding",
            col
        ].dropna()

        side = merged.loc[
            merged["source"] == "SideProject",
            col
        ].dropna()

        if (col == "avg_lines_in_comment"):
            vibe = vibe[vibe!=0]
            side = side[side!=0]

        if len(vibe) == 0 or len(side) == 0:
            continue

        stat, p = mannwhitneyu(
            vibe,
            side,
            alternative="two-sided"
        )
        delta = cliffs_delta(vibe, side)

        results.append({
            "feature": col,
            f"{"Vibecoding"}_n": len(vibe),
            f"{"SideProject"}_n": len(side),
            "p_value": p,
            "vibecoding_median": vibe.median(),
            "sideproject_median": side.median(),
            "vibecoding_mean": vibe.mean(),
            "sideproject_mean": side.mean(),
            "effect_direction":
                "Vibecoding > SideProject"
                if delta>0
                else "SideProject > Vibecoding",
            # "effect_direction":
            #     "Vibecoding > SideProject"
            #     if vibe.median() > side.median()
            #     else "SideProject > Vibecoding",
            "size": delta
        })

    results_df = pd.DataFrame(results)
    results_df["p_adj"] = multipletests(
    results_df["p_value"],
    method="fdr_bh"
    )[1]

    results_df["significant"] = (
        results_df["p_adj"] < 0.05
    )

    results_df = results_df.sort_values(
        "p_adj"
    )
    return results_df



def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    mask = (df_files["url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files


# print(folder_stats.head())


if __name__ == "__main__":
    ## files per language, # lines per extension, 
    # # of files, age of project, 
    # # of folders, 
    # Max depth of folder, avg files per folder

    #Number of warnings from pylint

    df = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
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
    # print(df_merged_all.size)
    print(df_merged_all.groupby("source")["url"].nunique())

    # of folders, Max depth of folder, avg files per folder
    folder_stats = (
    df_merged_all.groupby(["url", "source"])
      .apply(project_folder_stats)
      .reset_index()
    )
    # print(folder_stats.head())
    run_tests(df_merged_all)

    #Project Age
    project_age = pd.read_csv("../dataset_features/project_age.csv")


    project_age['days'] = project_age[' age'].str.extract(r"'age_days':\s*(\d+)")
    pattern = r'^https?://github\.com/[^,\s]+'
    project_age["url_source"] =[re.search(pattern, i[0]).group(0)  for i in project_age.index]
    project_age = project_age.drop("url", axis=1)
    size_age = folder_stats.merge(project_age, left_on="url", right_on="url_source", how="left")
    size_age["age"] = size_age["days"].fillna(-1).astype(int)
    size_age = size_age.drop("days",axis=1)
    size_age = size_age.drop(" age",axis=1)
    size_age = size_age.drop("url_source", axis=1)

    #Number of files
    counts = (
    df_merged_all
    .groupby([ "url",])
    .size()
    .reset_index(name="n_files")
    )
    counts.head()
    print(df_merged_all.groupby("source")["url"].nunique())

    df_merged = size_age.merge(counts, on="url", how="left")
    # print(df_merged.head())
    run_metric_tests(df_merged)
    print(df_merged.groupby("source")["url"].nunique())

    # files per extension, # lines per extension

    acceptable_exts = ['ts',  'tsx', 'markdown', 'md', 'mdx',  'xml', 'cs', 'py',  'js', 'mjs',  'cjs',  'ejs',  'rs',  'css', 
             'kt', 'html', 'sh',  'txt',  'sql',  'astro',  'go', 'c', 'cc',  'cpp',  'hpp', 'csproj',  'm',  'h', 
             'rb', 'tmlanguage', 'java', 'swift',  'ru', 'ipynb',  'bat',  'exe',  'kts', 'wasm',  'npmrc',  'nvmrc',  
             'sb',  'snap', 'http', 'ps1',  'php',  'woff2', 'sum', 'mako',  'ino',  'cmd',  'env', 'ahk',  'bash',  
             'erb', 'onnx',  'server', 'skill',  'tpl',  'class',  'mak', 'mk', 'lua', 's', 'dcu', 'less',  'pas',  
             'woff', 'scss', 'pyc', 'dpr', 'inc', 'res',  'resx',  'dproj',  'hex',  'idl',  'pl', 'bm2', 'dak',  
             'gradle',  'ld',  'rst' , 'wxs', 'bsd',  'el', 'htaccess',  'manifest', 'md~',  'vcxproj', '~pas',  
             'ap_',  'asm',  'bas',  'classpath',  'ddp',  'dex' , 'dist', 'htm',  'lircrc',  'makefile',  'odt', 
             'qml',  'qrc',  'rtf', 'sass', 'sch',  'skins2', 'tmpl', 'vbp', 'vbw',  'vim' , 'xsd', '~ddp', '~dpr', ]  # your list here

    df_filt = df_all[df_all["extn"].isin(acceptable_exts)].copy()

    project_ext_stats = (
        df_filt
        .groupby(["url", "source", "extn"])
        .agg(
            n_files_ext=("file_path", "count"),
            n_lines_ext=("n_lines", "sum")
        )
        .reset_index()
    )

    wide_ext_stats = project_ext_stats.pivot_table(
        index=["url", "source"],
        columns="extn",
        values=["n_files_ext", "n_lines_ext"],
        fill_value=0
    )

    wide_ext_stats.columns = [
        f"{metric}_{ext}" for metric, ext in wide_ext_stats.columns
    ]

    wide_ext_stats = wide_ext_stats.reset_index()

    merged = df_merged.merge(
    wide_ext_stats,
    on=["url", "source"],
    how="left"
)

    ext_cols = [
        c for c in merged.columns
        if c.startswith("n_files_ext_") or c.startswith("n_lines_ext_")
    ]

    merged[ext_cols] = merged[ext_cols].fillna(0)

    for col in merged.columns:
        if col.startswith("n_lines_ext_"):
            ext = col.removeprefix("n_lines_ext_")
            files_col = f"n_files_ext_{ext}"
            out_col = f"avg_file_len_for_{ext}"

            if files_col in merged.columns:
                merged[out_col] = np.divide(
                    merged[col],
                    merged[files_col],
                    out = np.full(len(merged), np.nan),
                    where=merged[files_col] != 0,
                )

    print(merged.groupby("source")["url"].nunique())
    merged.to_csv("proj_stats_new.csv")

    results_df = run_stats_tests(merged)

    results_df.to_csv("proj_level_results.csv")

