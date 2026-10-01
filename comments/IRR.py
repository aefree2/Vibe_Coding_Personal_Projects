import pandas as pd 
import argparse
from pathlib import Path
import math


if __name__ == "__main__":
    colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw_comment"] 
    comments = pd.read_csv("../dataset_features/comments.csv", names=colnames, header=None)
    comments.drop_duplicates(inplace=True)
    df=comments.sample(50,replace=False)
    df.to_csv("I_comments.csv")


    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    new_s = source.sample(50, replace=False)
    new_s["new_link"] = new_s["url"] + "/blob/" + new_s["commit"]
    new_s.to_csv("I_cat.csv")