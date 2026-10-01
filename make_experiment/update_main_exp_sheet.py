import pandas as pd
import argparse
from pathlib import Path
import numpy as np


def update_main_dataframe(url, commit, experiment_name, checkpoint_file):
    #print("HIIIIII")
    try:
        exp_df = pd.read_csv(checkpoint_file, index_col=0)
    except Exception as E:
        print(E)
        print("Problem with file, creating new dataframe.")
        exp_df = pd.DataFrame(columns=["url", "commit", "error", "time_out"]) #going to have to update this to contain timed out and error, set to false as default
    #if the experiment name is already in the dataframe
    if experiment_name not in exp_df.columns:
        #there is an error here
        exp_df[experiment_name] = False
    #if the project is already in the dataframe
    if url not in exp_df["url"].values:
        new_row = [url, commit, False, False] + [False] * (len(exp_df.columns) - 4)
        exp_df.loc[len(exp_df)] = new_row
    #print(exp_df.head())
    exp_df.loc[exp_df["url"] == url, experiment_name] = True
    exp_df.to_csv(checkpoint_file)

def remove_from_main_dataframe(url, checkpoint_file):
    exp_df = pd.read_csv(checkpoint_file, index_col=0)
    exp_df.loc[exp_df["repo"] == url, exp_df.columns[2:]] = False #look at this line
    exp_df.to_csv(checkpoint_file)

def remove_timed_out(url, checkpoint_file):
    exp_df = pd.read_csv(checkpoint_file, index_col=0)
    exp_df.loc[exp_df["url"] == url, "time_out"] = False
    exp_df.to_csv(checkpoint_file)

def get_value(url, col, checkpoint_file):
    exp_df = pd.read_csv(checkpoint_file, index_col=0)
    return exp_df.loc[exp_df["url"] == url, col].values[0]



def update_column_for_user( username, source, update_column, checkpoint_file):
    df = pd.read_csv(checkpoint_file, index_col=0)

    # Extract username from GitHub URL
    user_mask = df["url"].str.extract(r"github\.com/([^/]+)/")[0] == username

    # rows where username matches AND condition column is True
    mask = user_mask & (df["url"] == True)

    # Update the target column
    df.loc[mask, update_column] = True

    # Save changes
    df.to_csv(checkpoint_file)

    return df



if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Update the spreadsheet handling which project goes in which set of experiments")
    p.add_argument("--url", type=str)
    p.add_argument("--commit", type=str)
    p.add_argument("--experiment_name", type=str)
    p.add_argument("--checkpoint_file", default="main_exp_sheet.csv", type=Path)
    args = p.parse_args()
    
    try:
        exp_df = pd.read_csv(args.checkpoint_file, index_col=0)
    except:
        print("Problem with file, creating new dataframe.")
        exp_df = pd.DataFrame(columns=["url", "commit"])
    #if the experiment name is already in the dataframe
    if args.experiment_name not in exp_df.columns:
        exp_df[args.experiment_name] = False
    #if the project is already in the dataframe
    if args.url not in exp_df["url"].values:
        new_row = [args.url, args.commit] + [False] * (len(exp_df.columns) - 2)
        exp_df.loc[len(exp_df)] = new_row
    #print(exp_df.head())
    exp_df.loc[exp_df["url"] == args.url, args.experiment_name] = True
    exp_df.to_csv(args.checkpoint_file)
   
