import pandas as pd 
import argparse
from pathlib import Path
import math

def find_correct_sample( pop, Z = 1.96, p = 0.5, E=0.05):
    m = ((Z** 2) * p*(1-p))/(E**2)
    n = m/(1+ ((m-1)/pop))
    n = math.ceil(n)
    #print(f"number of samples: {n}")
    return n

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Subsample the total comments to the required amount.")
    p.add_argument("--comments", default="../dataset_features/comments.csv", type=Path) # "../backups/comments.csv"
    p.add_argument("--cat_source", default="../backups/exp_no_hist.csv",  type=Path)
    p.add_argument("--names",  nargs="+") 
    p.add_argument("--output_name", default="subsampled.csv" )
    args = p.parse_args()

   # comments = pd.read_csv(args.comments)
    
    #print(comments.head())
    #deduplicate the comments dataframe
    colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw_comment"] 
    comments = pd.read_csv(args.comments, names=colnames, header=None)
    comments.drop_duplicates(inplace=True)
    #print(comments.head)

    source = pd.read_csv(args.cat_source, index_col=0)
    print(len(comments))
    total_df = pd.DataFrame(columns=comments.columns)

    mask = (source["SideProject"] == True) & (source["Vibecoding"] == True)
    print()
    print(len(source[mask]))
    print()
    for name in args.names:
        mask = (source[name])
        name_df = source[mask]
        url_set = set(name_df["url"])
        mask = (comments["url"].isin(url_set))
        name_comments = comments[mask]
        n_samples = find_correct_sample(len(name_comments))
        #get the table thing in here
        
        print(f"{name}:\t{len(name_comments)}:\t{n_samples}")
        n_comments = len(name_comments)

        ##if grouping:
        group_comments = name_comments.groupby("url")
        for group in group_comments:
            #print(len(group[1]))
            n_sub_samples = math.ceil(n_samples * (len(group[1])/n_comments)) #double-check this line
            #n_sub_samples = find_correct_sample(len(group[1]))
            df=group[1].sample(n_sub_samples,replace=False)
            total_df = pd.concat([total_df, df])
            #print(f"{len(group[1])}: {n_sub_samples}: {len(df)}: {len(total_df)}")
        print(f"number of {name} projects with Python comments: {len(group_comments)}")
        print(n_samples)
        print(len(total_df))
    shuffle_total_df = total_df.sample(frac=1)
    # shuffle_total_df.to_csv("subsampled_comments.csv")
    print()
    print(len(shuffle_total_df))


    #print(source.head())

