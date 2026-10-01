#this file will
#A have a function to see if the main comitter is a the owner of repo
#b get all historical projects by a user
#c get the last commit before a specific date
from git_functions import get_user_repos, get_project_age, fetch_contributor_stats, summarize_contributors,  last_commit_before_date_github, is_repo_fork
from update_main_exp_sheet import update_main_dataframe, remove_timed_out
import argparse
import subprocess
import requests
from pathlib import Path


from urllib.parse import urlparse

def extract_github_repo_info(url: str):
    """
    Extract (username, repo_name) from a GitHub repository URL.
    
    Examples:
    https://github.com/user/repo
    https://github.com/user/repo.git
    https://github.com/user/repo/tree/main
    """
    
    parsed = urlparse(url)
    
    if parsed.netloc != "github.com":
        raise ValueError("Not a GitHub URL")
    
    parts = parsed.path.strip("/").split("/")
    
    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")
    
    username = parts[0]
    repo = parts[1].replace(".git", "")
    
    return username, repo


def make_history(url, sha, before_date, token, source, checkpoint_file):
    username, repo = extract_github_repo_info(url)
    print(url)
    print(f"{username}, {repo}")
    full_repo = f"{username}/{repo}"
    stats = fetch_contributor_stats(full_repo, token )
    is_top_c = False
    if stats:
        if stats == "ERROR":
            update_main_dataframe(f"https://github.com/{username}/{repo}", "ERROR" ,"error", checkpoint_file)
            return
        is_top_c = summarize_contributors(stats, username)
        remove_timed_out(url, checkpoint_file)
    else:
        update_main_dataframe(url, sha ,"time_out", checkpoint_file)
    
    if is_top_c:
        #if they are the top contributor of that repo, get their history
        print(f"Fetching Historical Stats")
        repos = get_user_repos(username=username, token=token)
        for repo in repos:
               if is_repo_fork(url, token):
                   continue
               #For each project, see if owner is top contributor
               commit = last_commit_before_date_github(username, repo, before_date, token=token) 
               #print(commit)
               if commit:
                if commit == "ERROR":
                    update_main_dataframe(f"https://github.com/{username}/{repo}", "ERROR" ,"error", checkpoint_file)
                    update_main_dataframe( f"https://github.com/{username}/{repo}", "ERROR" ,f"{source}_history", checkpoint_file)
                    continue
                stats = fetch_contributor_stats(f"{username}/{repo}", token)
                is_top_c_hist = False
                if stats:
                        if stats == "ERROR":
                            update_main_dataframe(f"https://github.com/{username}/{repo}", commit["sha"] ,"error", checkpoint_file)
                            update_main_dataframe( f"https://github.com/{username}/{repo}", commit["sha"] ,f"{source}_history", checkpoint_file)
                            continue

                        is_top_c_hist = summarize_contributors(stats, username)
                        if is_top_c_hist:
                            #if yes, check to see if there is a commit from before the cuttoff date
                            print(f"{repo} is in dataset")
                            update_main_dataframe( f"https://github.com/{username}/{repo}", commit["sha"] ,f"{source}_history", checkpoint_file)
                            update_main_dataframe( args.url, sha ,f"{source}_control", checkpoint_file)
                            write_to_age(f"https://github.com/{username}/{repo}", commit["author_date"], token)
                            remove_timed_out(url, checkpoint_file) #this is the thing that is causing the bug, it gracefully creates the url
                else:
                    update_main_dataframe(f"https://github.com/{username}/{repo}", commit["sha"] ,"time_out", checkpoint_file)
                    update_main_dataframe( f"https://github.com/{username}/{repo}", commit["sha"] ,f"{source}_history", checkpoint_file)
                    


#write another timed-out file, update main_exp_sheet to be able to set things to false
  
def append_if_not_exists_fast(csv_path, url, age):
    try:
        with open(csv_path, "r") as f:
            for row in f:
                if url in row:
                    return False
    except FileNotFoundError:
        pass

    with open(csv_path, "a") as f:
        f.write(f"{url}, {age}\n")

    return True


def write_to_age(url, target_date, token):
    try:
        age = get_project_age(repo_url=url, target_date=target_date, token=token)
    except Exception as e:
        update_main_dataframe(f"https://github.com/{username}/{repo}", "ERROR" ,"error", args.checkpoint_file)

        return
    #print(age)
    append_if_not_exists_fast("../dataset_features/project_age.csv", url, age) #remove hard coding here

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Get the github data")
    p.add_argument("--url", type=str)
    p.add_argument("--experiment_name", type=str)
    p.add_argument("--checkpoint_file", type=Path)
    p.add_argument("--before_date", default= "11-29-2022",type=str)
    p.add_argument("--current_date", default= "03-11-2026",type=str) #I need to check and replace these as I go
    p.add_argument("--token",type=str)
    p.add_argument("--history", choices=["True", "False"])
    args = p.parse_args()
    #print(f"Running Experiments With:\t URL: {args.url} \t Experiment: {args.experiment_name} \t Current date: {args.current_date} \t Historical Cuttoff: {args.before_date}")
    
    #Update the main dataframe
    #split the url into string components
    username, repo = extract_github_repo_info(args.url)
    #get latest commit before date
    commit = last_commit_before_date_github(owner=username, repo=repo, before_iso=args.current_date, token=args.token) #fixed, passed in from command line arguments
    if (commit == "ERROR") or commit == None:
        update_main_dataframe(f"https://github.com/{username}/{repo}", "ERROR" ,"error", args.checkpoint_file)
        update_main_dataframe( f"https://github.com/{username}/{repo}", "ERROR" ,f"{args.experiment_name}", args.checkpoint_file)
        if commit == None:
            append_if_not_exists_fast("../dataset_features/errored_out.csv", args.url, f"no commit before {args.current_date}")

    else:
        if not is_repo_fork(args.url, args.token):
            update_main_dataframe (args.url, commit["sha"], args.experiment_name, args.checkpoint_file)
            write_to_age(args.url, commit["author_date"], args.token)
            if args.history == "True":
                make_history(args.url, commit["sha"], args.before_date, args.token, args.experiment_name, args.checkpoint_file) #also fix this
        else:
            print("FORK")
            append_if_not_exists_fast("../dataset_features/errored_out.csv", args.url, f"is fork")

    #write to age_of_project
    #goes to dataset_features/age_of_project.csv
    




    #split url into username/repo name
    # job one, find all commits before a specific date (Sideproject)

    #job two, find most recent commit (Vibecoding)

    #job three, create history (Vibecoding)
    #take in url
    #make sure that the user is the main contributor

    #if yes, then get history of all projects by that user
    
    # for each project, make sure user is the main contributor
    # if yes, find last commit before cuttoff date
    # if it exists, then add to the spreadsheet

    #subprocess.run(["python3", "update_main_exp_sheet.py", args])