import requests
import time
import pandas as pd
import os
import argparse

# --------- CONFIG ---------
#REPO = "owner/repo"  # e.g., "torvalds/linux"
#GITHUB_TOKEN = None  # Or set to a string if you want to authenticate
# --------------------------

HEADERS = {"Accept": "application/vnd.github+json"}
GITHUB_TOKEN  = os.getenv('GITHUB_TOKEN')
#GITHUB_TOKEN = "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"

#INPUT_FILE = "../Rules Extended - clean_experiment.csv"#"total_list.csv"
OUTPUT_FILE = "../raw_data/filtered_experiment.csv"

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

def fetch_contributor_stats(repo):
    url = f"https://api.github.com/repos/{repo}/stats/contributors"
    print(f"Fetching contributor stats for {repo}...")

    # Sometimes GitHub returns 202 if data is being generated
    for _ in range(100):
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 202:
            print("GitHub is generating stats... waiting...")
            time.sleep(2)
            continue
        elif response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    print("Timed out waiting for GitHub to generate stats.")
    return None

def summarize_contributors(data, owner):
    contributor_list = []
    total_commits_proj = 0
    for contributor in data:
        if contributor["author"]:
            username = contributor["author"]["login"]
            total_commits = contributor["total"]
            weeks = contributor["weeks"]
            additions = sum(week["a"] for week in weeks)
            deletions = sum(week["d"] for week in weeks)
            total_commits_proj = total_commits_proj + total_commits

            print(f"User: {username}")
            print(f"  Commits  : {total_commits}")
            print(f"  Additions: {additions}")
            print(f"  Deletions: {deletions}")
            print("-" * 30)
            contributor_list.append([username, additions + deletions])
        else:
            print("There is no author!")
    sorted_list = sorted(contributor_list, key=lambda x: x[1], reverse=True)
    return sorted_list[0][0] == owner
    

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Interactively accept/reject NDJSON lines by viewing `body`.")
    p.add_argument("--input_file", type=str)
    p.add_argument("--output_file", type=str)
    p.add_argument("-checkpointing", type=bool)
    args = p.parse_args()

    dataframe = pd.read_csv(args.input_file)
    if args.checkpointing:
        output_dataframe = pd.read_csv(args.output_file)
        processed_ids = set(output_dataframe["Project name"])
        dataframe = dataframe[~dataframe["Project name"].isin(processed_ids)]
    else:
        output_dataframe = pd.DataFrame(columns=["Username", "Project name", "origional project"])
    #print(dataframe.head())
    for i, row in dataframe.iterrows():
        values = row["Username"] + "/" + row["Project name"]
        stats = fetch_contributor_stats(values)
        is_good = False
        if stats:
            is_good = summarize_contributors(stats, row["Username"])
            print(is_good)
        if is_good:
            print(row)
            output_dataframe = pd.concat(
                                [output_dataframe, pd.DataFrame([row], columns=output_dataframe.columns)],
                                ignore_index=True
)
            #output_dataframe.loc[len(output_dataframe)] = row
            #print(output_dataframe)
            output_dataframe.to_csv(args.output_file, index=False)
            
    output_dataframe.to_csv(args.output_file, index=False)
