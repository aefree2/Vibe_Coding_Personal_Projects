from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token
import pandas as pd
from bisect import bisect_right
import argparse
import re
import csv


#Is given a python file, will create and append to a csv with the 
#Project URL (raw) | project url (updated with location info to hyperlink to comment) | Location of comment | Comment

def append_if_not_exists(df, row):

    if not (df == row).all(axis=1).any():
        df.loc[len(df)] = row

def append_raw_csv(location, row):
    with open(location,'a') as fd:
        writer = csv.writer(fd)
        writer.writerow(row)

def load_from_checkpoint(path):
    try:
        df = pd.read_csv(path, index_col=0)
    except:
        print("error reading in file")
        df = pd.DataFrame(columns = ["url", "commit", "proj_name", "file_path", "file_name", "new_url", "comments"], dtype=object)
    return df

def format_context_block(entry) -> str:
    return "\n".join(entry["context_lines"])

def extract_comments_and_docstrings(code):
    """
    Extract all line comments (# ...) and docstrings from Python source code.
    Returns a list of strings.
    """
    comments = []

    for token_type, token_value in lex(code, PythonLexer()):
        if token_type in Token.Comment or token_type is Token.String.Doc:
            comments.append(token_value)

    return comments


def extract_comments_and_docstrings_with_context(code, before=2, after=2):
    """
    Extract comment blocks (# ...) and docstrings with surrounding context.

    Consecutive line comments are merged into a single comment block
    only when each comment is the only thing on its line.

    For each match, returns a dict:
      {
        "token_text": str,
        "kind": "comment" | "docstring",
        "start_line": int,                 # 1-based
        "end_line": int,                   # 1-based
        "context_lines": [str, ...],
        "context_start_line": int          # 1-based
      }
    """
    lines = code.splitlines()
    lexer = PythonLexer()

    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    def offset_to_line_idx(char_offset: int) -> int:
        return max(0, bisect_right(line_starts, char_offset) - 1)

    def is_standalone_comment(offset: int, start_idx: int, end_idx: int) -> bool:
        """
        True only if this is a single-line comment and the comment is the only
        thing on the line except leading whitespace.
        """
        if start_idx != end_idx:
            return False

        line = lines[start_idx]
        line_offset = offset - line_starts[start_idx]
        prefix = line[:line_offset]

        return prefix.strip() == ""

    raw_items = []

    for offset, token_type, token_value in lexer.get_tokens_unprocessed(code):
        is_comment = token_type in Token.Comment
        is_doc = token_type is Token.String.Doc

        if not (is_comment or is_doc):
            continue

        start_idx = offset_to_line_idx(offset)
        end_offset = max(offset, offset + len(token_value) - 1)
        end_idx = offset_to_line_idx(end_offset)

        raw_items.append({
            "token_text": token_value,
            "kind": "docstring" if is_doc else "comment",
            "start_idx": start_idx,
            "end_idx": end_idx,
            "standalone": is_comment and is_standalone_comment(offset, start_idx, end_idx),
        })

    merged = []
    i = 0
    while i < len(raw_items):
        item = raw_items[i]

        if item["kind"] != "comment":
            merged.append(item)
            i += 1
            continue

        # Only standalone comment lines are eligible to be merged
        if not item["standalone"]:
            merged.append(item)
            i += 1
            continue

        start_idx = item["start_idx"]
        end_idx = item["end_idx"]
        token_parts = [item["token_text"]]

        j = i + 1
        while j < len(raw_items):
            nxt = raw_items[j]

            if nxt["kind"] != "comment":
                break

            # Only merge standalone comment lines on immediately consecutive lines
            if nxt["standalone"] and nxt["start_idx"] == end_idx + 1:
                end_idx = nxt["end_idx"]
                token_parts.append(nxt["token_text"])
                j += 1
            else:
                break

        merged.append({
            "token_text": "\n".join(part.rstrip("\n") for part in token_parts),
            "kind": "comment",
            "start_idx": start_idx,
            "end_idx": end_idx,
        })
        i = j

    results = []
    for item in merged:
        start_idx = item["start_idx"]
        end_idx = item["end_idx"]

        ctx_start = max(0, start_idx - before)
        ctx_end = min(len(lines), end_idx + after + 1)

        results.append({
            "token_text": item["token_text"],
            "kind": item["kind"],
            "start_line": start_idx + 1,
            "end_line": end_idx + 1,
            "context_lines": lines[ctx_start:ctx_end],
            "context_start_line": ctx_start + 1,
        })

    return results

def extract_comments_and_docstrings_from_file(path, url):
    try:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
         df_failures = pd.read_csv("../dataset_features/clone_failures.csv", index_col=0)
         file_name = re.split(r"/", path)[-1]
         append_if_not_exists(df_failures, [url, file_name, path, f"comments failed: {e}"])
         print(e)
         return 
    return extract_comments_and_docstrings_with_context(code)

def find_comments(url, commit, short_name, file_path, path="../dataset_features/comments.csv"):
    print("finding comments")
    #df = load_from_checkpoint(path=path)

    #sample form of url
    #https://github.com/aefree2/VibecodingQuality/blob/e8d27079b7d443d8f33ebb6f4b0f3fd9b104e68c/raw_data/Experiment_extended_revised.csv#L5
    results = extract_comments_and_docstrings_from_file(file_path, url)
    #augment the file path
    

    if results:
        for comment in results:
            # print(f"comment: {comment}")
            
            temp_name = re.sub(r'^[^/]+/' ,"", file_path, count=1)
            updated_url = f"{url}/blob/{commit}/{temp_name}#L{comment["context_start_line"]}"
            file_name = re.split(r"/", file_path)[-1]
            #append_if_not_exists(df, [url, commit, short_name, file_path, file_name, updated_url, str(format_context_block(comment)), type, comment text])
            append_raw_csv(path,[url, commit, short_name, file_path, file_name, updated_url, str(format_context_block(comment)), comment["kind"], comment["token_text"]] )
            #df.loc[len(df)] = 
    #df.to_csv(path)
    return #df
                

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Cleaning the spreadsheet, because it does not work in bash.")
    p.add_argument("--url")
    p.add_argument("--commit")
    p.add_argument("--short_name")
    p.add_argument("--file_path")
    args = p.parse_args()
    
    