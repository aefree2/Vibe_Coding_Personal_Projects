import pandas as pd 
import argparse
from pathlib import Path
import math
from tabulate import tabulate

def get_file_proj_counts (extns, masked_files):
    print(masked_files["extn"].value_counts())
    py_value = masked_files["extn"].value_counts().get(extns, 0)

    # print(f"Number of Python files: {py_value}")


    n_python_proj =len( masked_files[masked_files['extn'].apply(lambda x: x == extns)].groupby("url"))

    # print(f"Number of projects with Python: {n_python_proj}")
    
    print()

    headers = ["cat", "total", "Python", "percent Python"]
    table = [["files", len(masked_files), py_value, f"{py_value/len(masked_files):.0%}"], 
                ["projects", n_proj, n_python_proj, f"{n_python_proj/n_proj:.0%}"]]
    print(tabulate(table, headers, tablefmt="github"))
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Subsample the total comments to the required amount.")
    p.add_argument("--files", default="../dataset_features/files_raw.csv", type=Path) # "../backups/comments.csv"
    p.add_argument("--cat_source", default="../backups/exp_no_hist.csv",  type=Path)
    p.add_argument("--names",  nargs="+") 
    p.add_argument("--output_name", default="subsampled.csv" )
    args = p.parse_args()


    # colnames=["url","commit","proj_name","file_path","file_name","new_url","comments"] #for later
    # comments = pd.read_csv(args.comments, names=colnames, header=None)

    files = pd.read_csv(args.files, index_col=0)
    files.drop_duplicates(inplace=True)
    print(files.head())


    source = pd.read_csv(args.cat_source, index_col=0)
    print(len(files))

    mask = (source["SideProject"] == True) & (source["Vibecoding"] == True)
    print()
    print(len(source[mask]))
    print()
    files["avg_char_line"] = files["n_characters"]/(files["lines"] - files["blank_lines"])
    for name in args.names:
        print(name)
        mask = (source[name])
        name_df = source[mask]
        url_set = set(name_df["url"])
        mask = (files["url"].isin(url_set))
        masked_files = files[mask]
        avg_lines = masked_files["lines"].mean()
        avg_char_line = masked_files["avg_char_line"].mean()
        #print(avg_char_line)

        n_proj = len(masked_files.groupby("url"))

        headers = ["total files", "average lines per file", "average characters per line", "average files per project"]
        table = [[len(masked_files),avg_lines, avg_char_line, len(masked_files)/n_proj]]
        print()

        print(tabulate(table, headers, tablefmt="github"))
        get_file_proj_counts("py", masked_files)
        
        

        #Python data gathering
  

