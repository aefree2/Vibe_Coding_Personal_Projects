from data_tinder import Checkpoint
from data_tinder import safe_json_loads
from pathlib import Path
import argparse
import re



def load_file(
    input_path: Path):

    with open(input_path, 'r') as fp:
        total_lines = [line for line in fp]
    return total_lines

def find_links(input_path: Path, output_path: Path, is_post=True):
    lines = load_file(input_path)
    field = "body"
    all_links = []
    if is_post:
        field = "selftext"
    for line in lines:
        obj = safe_json_loads(line)
        text = str(obj.get(field, ""))
        post_github = re.findall(r"https://github\.com/[^/\s)]+/[^]|)|\s|/]+", text) 
        #made a decision here to cut the links down to the exact repo... unsure if this will have consequences 
        #may need to be stricter with what does and does not count as a link
        #I chose to cut them down to deal with the /commit_x problem, as restricting those would be too big of an issue, and they would clone correctly


        for link in post_github:
        #print(link)
            all_links.append(link)
    print(len(all_links))
    all_links = list(set(all_links))
    print(len(all_links))
    with open(output_path, 'w') as f:
        for line in all_links:
            f.write(f"{line}\n")
     
     


def main ():
    p = argparse.ArgumentParser(description="scrape all links from a list of posts.")
    
    p.add_argument("--subreddit_name", type=Path, help="path to the FILE we are trying to find")
    p.add_argument("--input", type=Path,default=Path("reddit_sorting"), help="path to the FOLDER where everything is.")
    p.add_argument("--output", type=Path, default=Path("dataset_features"))
    p.add_argument("--post", type = bool, default=True, help="if the set of files comes from a post or not")
    p.add_argument("--encoding", type=str, default="utf-8", help="Input encoding (default: utf-8)")
    args = p.parse_args()
    if args.post:
       post_type = "submissions"
    else:
       post_type == "comments"
    #reddit_sorting/Vibecoding_submissions_links_accepts.ndjson
    input_path = Path(f"{args.input}/{args.subreddit_name}_{post_type}_links_accepts.ndjson")
    output_path = Path(f"{args.output}/{args.subreddit_name}_github.txt")
    find_links(input_path, output_path)

if __name__ == "__main__":
    main()
