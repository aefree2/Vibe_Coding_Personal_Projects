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
from ast import literal_eval
import re
import ast
import tokenize
from scipy.stats import chi2_contingency, fisher_exact
from pathlib import Path
from statsmodels.stats.proportion import proportions_ztest

def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    df_files["short_url"] = df_files["URL"].str.split(r"/blob/").str[0]
    print(df_files["short_url"])
    mask = (df_files["short_url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files

if __name__ == "__main__":
    topic_df = pd.read_csv("Topics_2 - all_topics.csv")
    
    topic_df.dropna(subset=['URL'], inplace=True)
    # print(topic_df.head())
    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]
    py_vc = make_mask(source, topic_df, names[0])
    py_sp = make_mask(source, topic_df, names[1])

    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    df_all = pd.concat([py_sp, py_vc], ignore_index=True)
    print(df_all.head())
    print(df_all.source.value_counts())
    print(topic_df.shape)
    print(df_all.shape)
    symmetric_diff = set(topic_df["URL"]) ^ set(df_all["URL"])
    print(symmetric_diff)

    counts = pd.crosstab(df_all["Top"], df_all["source"])


    results = []
    table = pd.crosstab(df_all["Top"], df_all["source"])

    sp_total = table["SideProject"].sum()
    vb_total = table["Vibecoding"].sum()

    results = []

    for cat in table.index:
        sp = table.loc[cat, "SideProject"]
        vb = table.loc[cat, "Vibecoding"]

        z, p = proportions_ztest(
            [sp, vb],
            [sp_total, vb_total]
        )

        results.append({
            "Top": cat,
            "p_sideproject": sp / sp_total,
            "p_vibecoding": vb / vb_total,
            "difference": vb / vb_total - sp / sp_total,
            "p": p
        })

    results = pd.DataFrame(results)

    results["p_adj"] = multipletests(
        results["p"],
        method="fdr_bh"
    )[1]

    results["p_adj"] = multipletests(
    results["p"],
    method="fdr_bh"
    )[1]

    results["significant"] = results["p_adj"] < 0.05
    results= results.sort_values("p_adj")

    results["difference"] = (
    results["p_vibecoding"]
    - results["p_sideproject"]
)

    results["cohens_h"] = (
        2 * np.arcsin(np.sqrt(results["p_vibecoding"]))
        - 2 * np.arcsin(np.sqrt(results["p_sideproject"]))
    )

    results["direction"] = np.select(
    [
        results["cohens_h"] > 0,
        results["cohens_h"] < 0,
    ],
    [
        "More common in Vibecoding",
        "More common in SideProject",
    ],
    default="Equal frequency" )

    results["cohens_h_abs"] = results["cohens_h"].abs()

    results["effect_size"] = pd.cut(
        results["cohens_h_abs"],
        bins=[0, 0.2, 0.5, 0.8, np.inf],
        labels=["Negligible", "Small", "Medium", "Large"]
    )
    
    results.to_csv("sig_diff.csv")

    #####################################################sub-categories

    df_all

    df_all["last_category"] = df_all["Sub"].str.split(":").str[-1].str.strip()
    df_all["true_last"] = df_all["Top"] + " | "+ df_all["last_category"]

    # counts = pd.crosstab(df_all["t"], df_all["source"]).reset_index()


    results_2 = []
    table = pd.crosstab(df_all["true_last"], df_all["source"])

    sp_total = table["SideProject"].sum()
    vb_total = table["Vibecoding"].sum()

    results_2 = []

    for cat in table.index:
        
        sp = re.split(r"\|", cat)
        sp = sp[0].strip()
        sp_total= counts.loc[sp,"SideProject"]
        vc_total= counts.loc[sp,"Vibecoding"]

        
        
        sp = table.loc[cat, "SideProject"]
        vb = table.loc[cat, "Vibecoding"]

        z, p = proportions_ztest(
            [sp, vb],
            [sp_total, vc_total]
        )

        results_2.append({
            "sub": cat,
            "p_sideproject": sp / sp_total,
            "p_vibecoding": vb / vc_total,
            "difference": vb / vc_total - sp / sp_total,
            "p": p
        })

    results_2 = pd.DataFrame(results_2)

    results_2["p_adj"] = multipletests(
        results_2["p"],
        method="fdr_bh"
    )[1]

    results_2["p_adj"] = multipletests(
    results_2["p"],
    method="fdr_bh"
    )[1]

    results_2["significant"] = results_2["p_adj"] < 0.05
    results_2= results_2.sort_values("p_adj")

    results_2["difference"] = (
    results_2["p_vibecoding"]
    - results_2["p_sideproject"]
)

    results_2["cohens_h"] = (
        2 * np.arcsin(np.sqrt(results_2["p_vibecoding"]))
        - 2 * np.arcsin(np.sqrt(results_2["p_sideproject"]))
    )

    results_2["direction"] = np.select(
    [
        results_2["cohens_h"] > 0,
        results_2["cohens_h"] < 0,
    ],
    [
        "More common in Vibecoding",
        "More common in SideProject",
    ],
    default="Equal frequency" )

    results_2["cohens_h_abs"] = results_2["cohens_h"].abs()

    results_2["effect_size"] = pd.cut(
        results_2["cohens_h_abs"],
        bins=[0, 0.2, 0.5, 0.8, np.inf],
        labels=["Negligible", "Small", "Medium", "Large"]
    )
    
    results_2.to_csv("sub_dif.csv")

    ##################How to run project

    
    df_long = (
    df_all.assign(
        value=df_all["Tags"].str.split(",")
    )
    .explode("value")
)
    print(df_long.head())
    print(df_long.columns[df_long.columns.duplicated()])

    df_long["value"] = df_long["value"].str.strip()

    # counts = (
    # pd.crosstab(
    #     df_long["value"],
    #     df_long["source"]
    # )
    # .reset_index()
    # )
    # counts = df_long.groupby(["source", "value"]).size()
    counts = (
    df_long.groupby(["source", "value"])
    .size()
    .reset_index(name="count")
    )
    counts_wide = (
    counts
    .pivot_table(
        index="value",
        columns="source",
        values="count",
        fill_value=0
    )
)


    print(counts_wide)



    sp_total = counts_wide["SideProject"].sum() #here is my error, I should be summing overy type and other respectivly 
    vb_total = counts_wide["Vibecoding"].sum()
    # print(counts_wide.columns)
    sp_total = 315
    vb_total = 209

    results_1 = []

    for _, row in counts_wide.iterrows():
        if row.name in ["Involves AI (Maddy)", "AI only", "No code?", "Good Quote", "HUH", "Weird Local Host"]:
            continue
        print(row)

        sp = row["SideProject"]
        vb = row["Vibecoding"]
        # print(sp,vb)

        z, p = proportions_ztest(
            [sp, vb],
            [sp_total, vb_total]
        )

        p_sp = sp / sp_total
        p_vb = vb / vb_total

        h = (
            2 * np.arcsin(np.sqrt(p_vb))
            - 2 * np.arcsin(np.sqrt(p_sp))
        )

        results_1.append({
            "value": _,
            "SideProject": sp,
            "Vibecoding": vb,
            "p_sideproject": p_sp,
            "p_vibecoding": p_vb,
            "difference": p_vb - p_sp,
            "cohens_h": h,
            "direction": (
                "Vibecoding"
                if h > 0
                else "SideProject"
                if h < 0
                else "Equal"
            ),
            "p": p,
        })

    results_1 = pd.DataFrame(results_1)

    results_1["p_adj"] = multipletests(
        results_1["p"],
        method="fdr_bh"
    )[1]

    results_1 = results_1.sort_values("p_adj")
    results_1.to_csv("type_counts.csv")



        # counts of how to run project