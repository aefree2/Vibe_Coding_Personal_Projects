
from git_functions import fetch_contributor_stats, summarize_contributors, last_commit_before_date_github
from find_history import extract_github_repo_info, write_to_age, make_history
from update_main_exp_sheet import update_main_dataframe, remove_from_main_dataframe, remove_timed_out, update_column_for_user, get_value
import argparse
from pathlib import Path
import pandas as pd

#basically what this file is going to do is to retry the history,
#it does that by reading in the target csv, deleting the csv, and then running the problem again.
#running the problem again will cause it to write to the timed_out.csv again


def get_links_by_flag(csv_path, link_column, flag_column, flag_value):
    df = pd.read_csv(csv_path)

    links = df.loc[df[flag_column] == flag_value, link_column].tolist()

    return links


def retry_history(url, before_date, token, source):
    #ERROR HERE
    # NEW ERROR, if child is on timeout, and parent is on timeout, and child is recovered but parent is not there will be a floating child.
    # Control flow is such that if a parent times out, the child will be unreachable, error resolved (I think)

    # NEW ERROR, if one of the main files has an unreachable history, will have to get new children
    # I think I have resolved it now
    username, repo = extract_github_repo_info(url)
    if get_value(url,source,args.checkpoint_file):
        commit = last_commit_before_date_github(owner=username, repo=repo, before_iso=args.current_date, token=args.token)
        make_history(url, commit["sha"], before_date, token, source, args.checkpoint_file)
    
    else:
        
        commit = last_commit_before_date_github(username, repo, before_date, token=token)
        if commit == "ERROR":
            update_main_dataframe(f"https://github.com/{username}/{repo}", "ERROR" ,"error",args.checkpoint_file)
            remove_timed_out(url, args.checkpoint_file)
            return
        #print(commit)
        stats = fetch_contributor_stats(f"{username}/{repo}", token)
        is_top_c_hist = False
        if stats:
                is_top_c_hist = summarize_contributors(stats, username)
                if is_top_c_hist:
                    #if yes, check to see if there is a commit from before the cuttoff date
                    print(f"{repo} is in dataset")
                    update_main_dataframe( f"https://github.com/{username}/{repo}", commit["sha"] ,f"{source}_history", args.checkpoint_file)
                    #update_main_dataframe(url, sha ,f"{source}_control", args.checkpoint_file)
                    write_to_age(f"https://github.com/{username}/{repo}", commit["author_date"], token)
                    remove_timed_out(url, args.checkpoint_file)
                    update_column_for_user( username, source, f"{source}_control", args.checkpoint_file)
                else:
                    remove_from_main_dataframe(url, commit["sha"], args.checkpoint_file)
        

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Get the github data")
    p.add_argument("--source", type=str)
    p.add_argument("--checkpoint_file", type=Path)
    p.add_argument("--before_date", default= "11-29-2022",type=str)
    p.add_argument("--current_date", default= "03-11-2026",type=str) ######
    p.add_argument("--history", choices=["True", "False"])
    p.add_argument("--token",type=str)
    args = p.parse_args()

    candidates = get_links_by_flag(args.checkpoint_file, "url", "time_out", True)
    for url in candidates:
        retry_history(url, args.before_date, args.token, args.source)
