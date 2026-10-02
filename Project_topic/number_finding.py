import pandas as pd
# import researchpy as rp
# import statsmodels.api as sm
# import scipy.stats as stats
# import statsmodels.formula.api as smf
# import gpboost as gpb
import numpy as np
# from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
# from sklearn.preprocessing import StandardScaler
# from scipy.stats import mannwhitneyu
# from statsmodels.stats.multitest import multipletests
# from ast import literal_eval
# import re
# import ast
# import tokenize
# from scipy.stats import chi2_contingency, fisher_exact
# from pathlib import Path
# from statsmodels.stats.proportion import proportions_ztest

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
    print(df_all.columns)

    exploded = df_all.explode("Tags")
    subset=exploded[df_all["Top"] == "Software for Computing"]
    subset=subset[subset["source"]=="Vibecoding"]

    ai_only = subset[subset["Tags"].apply(lambda tags: "Involves AI (Maddy)" in tags)]
    ai_only_count = len(ai_only)

    print(f"total: {len(subset)}, ai_only: {ai_only_count}")
