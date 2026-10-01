
import requests
from typing import Optional, Dict
from datetime import datetime, timezone
import os
import time

#LAST_BEFORE_DATE = 



#GITHUB_TOKEN  = os.getenv('GITHUB_TOKEN')
#GITHUB_TOKEN = "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"

#INPUT_FILE = "../Rules Extended - clean_experiment.csv"#"total_list.csv"
OUTPUT_FILE = "../raw_data/filtered_experiment.csv"

# if GITHUB_TOKEN:
#     HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"
#get all historical commits by user

def get_user_repos(username, token=None):
    """
    Return a list of repository names owned by a GitHub user.
    
    Parameters
    ----------
    username : str
        GitHub username
    token : str | None
        Optional GitHub token to increase rate limits
        
    Returns
    -------
    list[str]
        List of repository names
    """

    repos = []
    page = 1

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-fetcher"
    }

    if token:
        headers["Authorization"] = f"token {token}"

    while True:
        r = requests.get(
            f"https://api.github.com/users/{username}/repos",
            headers=headers,
            params={
                "per_page": 100,
                "page": page
            }
        )

        r.raise_for_status()
        data = r.json()

        if not data:
            break

        repos.extend(repo["name"] for repo in data)
        page += 1

    return repos


#see if the user is the main contributor
def fetch_contributor_stats(repo, token):
    HEADERS = {"Accept": "application/vnd.github+json"}
    if token:
        HEADERS["Authorization"] = f"token {token}"
    url = f"https://api.github.com/repos/{repo}/stats/contributors"
    print(f"Fetching contributor stats for {repo}...")

    # Sometimes GitHub returns 202 if data is being generated
    for _ in range(10):
        response = requests.get(url, headers=HEADERS)
        time.sleep(2)
        if response.status_code == 202:
            print("GitHub is generating stats... waiting...") #disambiguate this, what does 202 mean
            time.sleep(2)
            continue
        elif response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            append_if_not_exists_fast("../dataset_features/errored_out.csv", f"https://github.com/{repo}", f"{response.status_code} = {response.text}")
            return "ERROR" #change this line to return an error
    print("Timed out waiting for GitHub to generate stats.") 
    return None

def summarize_contributors(data, owner):
    contributor_list = []
    total_commits_proj = 0
    #print(data)
    for contributor in data:
        if contributor["author"]:
            username = contributor["author"]["login"]
            total_commits = contributor["total"]
            weeks = contributor["weeks"]
            additions = sum(week["a"] for week in weeks)
            deletions = sum(week["d"] for week in weeks)
            total_commits_proj = total_commits_proj + total_commits

            # print(f"User: {username}")
            # print(f"  Commits  : {total_commits}")
            # print(f"  Additions: {additions}")
            # print(f"  Deletions: {deletions}")
            # print("-" * 30)
            contributor_list.append([username, additions + deletions])
        else:
            print("There is no author!")
    sorted_list = sorted(contributor_list, key=lambda x: x[1], reverse=True)
    time.sleep(2)
    return sorted_list[0][0] == owner

#finds the last commit before a specific date
def last_commit_before_date_github(
    owner: str,
    repo: str,
    before_iso: str,
    token: Optional[str] = None,
    branch: Optional[str] = None,
    timeout: float = 20.0,
) -> Optional[Dict[str, str]]:
    """
    Return the last commit at or before `before_iso` on GitHub, using the REST API.

    Args:
      owner, repo: GitHub repo coordinates
      before_iso: ISO8601 string, e.g. "2024-01-15T00:00:00Z"
      token: optional GitHub token to avoid low unauth limits
      branch: optional branch/ref (passed as `sha` in the API)
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "commit-finder",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "per_page": 1,          # only need the newest commit <= until
        "until": before_iso,    # API filters commits by date
    }
    if branch:
        params["sha"] = branch

    r = requests.get(url, headers=headers, params=params, timeout=timeout)

    if r.status_code == 451:
        print(f"{owner}/{repo} unavailable for legal reasons (DMCA)")
        append_if_not_exists_fast("../dataset_features/errored_out.csv", f"https://github.com/{owner}/{repo}", f"{r.status_code} unavailable for legal reasons (DMCA)")
        return "ERROR"

    if r.status_code == 404:
        print(f"{owner}/{repo} not found or private")
        append_if_not_exists_fast("../dataset_features/errored_out.csv", f"https://github.com/{owner}/{repo}", f"{r.status_code} not found or private")
        return "ERROR"

    if r.status_code == 409:
        print(f"{owner}/{repo} empty repository")
        append_if_not_exists_fast("../dataset_features/errored_out.csv", f"https://github.com/{owner}/{repo}", f"{r.status_code} empty repository")
        return "ERROR"
    if r.status_code == 403:
        print(f"{owner}/{repo} private repository or rate limited")
        append_if_not_exists_fast("../dataset_features/errored_out.csv", f"https://github.com/{owner}/{repo}", f"{r.status_code} private repository or rate limited")
        return "ERROR"


    r.raise_for_status()
    data = r.json()

    if not data:
        return None

    c = data[0]
    try:
        message = c["commit"]["message"].splitlines()[0]
    except Exception as E:
        print(f"{E}: {c["commit"]["message"]}")
        message = ""
    return {
        "sha": c["sha"],
        "author_date": c["commit"]["author"]["date"],
        "message": message,
        # "html_url": c.get("html_url", ""),
    }

#gets the most recent commit
def get_latest_commit_github(owner: str, repo: str, token: str | None = None):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-checker"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"

    params = {"per_page": 1}

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()

    commit = r.json()[0]

    return {
        "sha": commit["sha"],
        "date": commit["commit"]["author"]["date"],
        "message": commit["commit"]["message"].splitlines()[0]
    }

#get age of project


def get_project_age(
    repo_url: str, target_date: str, token: Optional[str] = None
):
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    owner, repo = parts[-2], parts[-1]

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-age",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        timeout=20,
    )

    if r.status_code != 200:
        append_if_not_exists_fast("../dataset_features/errored_out.csv", repo_url, "Error getting age")
        raise RuntimeError(
            f"GitHub API error {r.status_code} for {owner}/{repo}: {r.text}"
        )

    repo_info = r.json()
    created_at = datetime.fromisoformat(repo_info["created_at"].replace("Z", "+00:00"))
    target = datetime.fromisoformat(target_date.replace("Z", "+00:00"))

    return {
        "repo": f"{owner}/{repo}",
        "created_at": created_at,
        "target_date": target,
        "age_days": (target - created_at).days,
    }

def is_repo_fork(repo_url: str, token: str | None = None) -> bool:
    """
    Returns True if the GitHub repository is a fork, False otherwise.
    
    repo_url: https://github.com/owner/repo
    """

    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    owner, repo = parts[-2], parts[-1]

    url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-checker"
    }

    if token:
        headers["Authorization"] = f"token {token}"

    r = requests.get(url, headers=headers)

    if r.status_code == 404:
        raise ValueError(f"Repository {owner}/{repo} not found or inaccessible")

    r.raise_for_status()

    data = r.json()

    return data.get("fork", False)

# def get_project_age(repo_url: str, target_date: str, token=None):
#     """
#     Compute project age from first commit to a specific date.

#     repo_url: https://github.com/owner/repo
#     target_date: ISO string e.g. "2024-01-01T00:00:00Z"
#     """

#     parts = repo_url.rstrip("/").replace(".git", "").split("/")
#     owner, repo = parts[-2], parts[-1]

#     headers = {
#         "Accept": "application/vnd.github+json",
#         "User-Agent": "repo-age"
#     }

#     if token:
#         headers["Authorization"] = f"token {token}"

#     page = 1
#     first_commit = None

#     while True:
#         r = requests.get(
#             f"https://api.github.com/repos/{owner}/{repo}/commits",
#             headers=headers,
#             params={"per_page": 100, "page": page}
#         )

#         r.raise_for_status()
#         commits = r.json()

#         if not commits:
#             break
        
#         first_commit = commits[-1]
#         page += 1

#         if first_commit is None:
#             return None

        

#     first_date = datetime.fromisoformat(
#         first_commit["commit"]["author"]["date"].replace("Z", "+00:00")
#     )

#     target = datetime.fromisoformat(target_date.replace("Z", "+00:00"))

#     age_days = (target - first_date).days

#     return {
#         "repo": f"{owner}/{repo}",
#         "first_commit": first_date,
#         "target_date": target,
#         "age_days": age_days
#     }


def append_if_not_exists_fast(csv_path, url, reason):
    try:
        with open(csv_path, "r") as f:
            for row in f:
                if url in row:
                    return False
    except FileNotFoundError:
        pass

    with open(csv_path, "a") as f:
        f.write(f"{url}, {reason}\n")

    return True