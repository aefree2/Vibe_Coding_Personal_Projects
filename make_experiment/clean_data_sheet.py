import pandas as pd
import argparse
from pathlib import Path
import numpy as np

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Cleaning the spreadsheet, because it does not work in bash.")
    p.add_argument("--checkpoint_file", default="../backups/exp_no_hist.csv", type=Path)
    p.add_argument("--names",  nargs="+")
    p.add_argument("--output_name", default="clean_main_exp_sheet.csv" )
    args = p.parse_args()


    df = pd.read_csv(args.checkpoint_file, index_col=0)
    print(df.head)
    df_clean = pd.DataFrame(columns=df.columns)
    print(args.names)

    for _, row in df.iterrows():
        if row["error"]:
            # print("ERROR")
            continue
        elif row["time_out"]:
            print("time_out")
            valid = False
            for name in args.names:
                if row[name]:
                    valid = True
            if valid:
                #append to end of other dataframe.
                df_clean.loc[len(df_clean)] = row
            else:
                continue
        else:
            df_clean.loc[len(df_clean)] = row
    print(len(df))
    print(len(df_clean))

    new_df = df_clean[['url', 'commit']]
    new_df.to_csv("../dataset_features/new_csv.csv", index=False, header=False)