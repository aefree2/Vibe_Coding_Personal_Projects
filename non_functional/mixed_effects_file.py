import pandas as pd
# import researchpy as rp
# import statsmodels.api as sm
# import scipy.stats as stats
# import statsmodels.formula.api as smf
# import gpboost as gpb
import numpy as np
# from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
# from sklearn.preprocessing import StandardScaler
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    mask = (df_files["url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files


def cliffs_delta(x, y):
    x = np.asarray(x)
    y = np.asarray(y)

    greater = 0
    less = 0

    for xi in x:
        greater += np.sum(xi > y)
        less += np.sum(xi < y)

    return (greater - less) / (len(x) * len(y))

if __name__ == "__main__":
    # Lines, blank lines, characters (average line length), extension
    df = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    df.drop_duplicates(inplace=True)
    source= pd.read_csv( "../backups/exp_no_hist.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]

    #make paired dataset

    py_vc = make_mask(source, df, names[0])
    py_sp = make_mask(source, df, names[1])

    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    df_all = pd.concat([py_sp, py_vc], ignore_index=True)
    df_all

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

    df_all = pd.concat([df_failed_all, df_all], join='outer', axis=0, ignore_index=True)

    acceptable_exts = ['ts', 'md', 'sh', 'scss', 'py',  'js', 'java', 'go', 'cs'] 

    results = []

    for extn, group in df_all.groupby("extn"):
        # print(group)
        if extn not in acceptable_exts:
            # print(extn)
            continue


        vibe = group[group["source"] == "Vibecoding"]
        side = group[group["source"] == "SideProject"]

        # need observations in both groups
        if len(vibe) < 5 or len(side) < 5:
            continue

        for metric in ["n_lines", "blank_lines", "char"]:

            x = vibe[metric].dropna()
            y = side[metric].dropna()

            if len(x) < 5 or len(y) < 5:
                continue

            print(x)

            stat, p = mannwhitneyu(
                x,
                y,
                alternative="two-sided"
            )
            delta = cliffs_delta(vibe, side)

            results.append({
                "extn": extn,
                "metric": metric,
                "n_vibecoding": len(x),
                "n_sideproject": len(y),
                "vibecoding_median": x.median(),
                "sideproject_median": y.median(),
                "vibecoding_mean": x.mean(),
                "sideproject_mean": y.mean(),
                "p_value": p,
                "effect_direction":
                "Vibecoding > SideProject"
                if delta>0
                else "SideProject > Vibecoding",
            # "effect_direction":
            #     "Vibecoding > SideProject"
            #     if vibe.median() > side.median()
            #     else "SideProject > Vibecoding",
                "size": delta,
                
            })

    results_df = pd.DataFrame(results)

    results_df["p_adj"] = multipletests(
    results_df["p_value"],
    method="fdr_bh"
    )[1]

    results_df["significant"] = (
        results_df["p_adj"] < 0.05
    )

    results_df = results_df.sort_values("p_adj")
    results_df.to_csv("file_level.csv")