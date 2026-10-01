#walk through entire file project
import os
import argparse
import pandas as pd
import re
from get_comments import find_comments
from get_imports import find_imports, find_requirements
from get_functions import find_functions, find_classes, find_all_calls
import csv

def append_if_not_exists(df, row):

    if not (df == row).all(axis=1).any():
        df.loc[len(df)] = row

def append_raw_csv(location, row):
    # return #REMEMBER THAT I DID THIS AND IF I DO THIS AGAIN I NEED TO TURN THIS LINE OFF DO NOT FORGET !!!!!!!!!!!!!!!!!!
    with open(location,'a') as fd:
        writer = csv.writer(fd)
        writer.writerow(row)

def line_finder(file_path):
    blank_lines = 0
    lines = 0
    line_len_sum = 0
    with open(file_path, 'r') as fp:
        #lines = sum(1 for line in fp)
        for line in fp:
            lines = lines+1
            line_len_sum = line_len_sum + sum(len(word) for word in line.split())
            #print(line.split())
            #print(sum(len(word) for word in line.split()))
            if line.split() == []:
                #print("EMPTY LINE")
                blank_lines = blank_lines +1
    return lines, blank_lines, line_len_sum

def files_finder(dir_name, url, commit):
    #walk through new one and get all python files
    # I don't know if I even need this bit ...
    # try:
    #     df = pd.read_csv("../dataset_features/files_raw.csv", index_col=0)
    #     # df_failures = pd.read_csv("../dataset_features/clone_failures.csv", index_col=0) (change to touch)
    # except Exception as e:
    #     print(e)
    #     df = pd.DataFrame(columns=["url", "proj_name", "full_path", "file_name", "extn", "lines", "blank_lines", "n_characters"])
    #     df_failures = pd.DataFrame(columns=["url", "proj_name", "file_name", "cause"])

    for (root, dirs, file) in os.walk(f"{str(dir_name)}"):
        # print("HERE")
        # print(f"{root}, {dirs}, {file}")
        for f in file:
            # print(f"{root}/{f}")
            full_path = f"{root}/{f}"
            extn = re.split(r"\.", f)[len(re.split(r"\.", f))-1]
            try:
                lines, blank_lines, avg_line_len = line_finder(full_path)
                #print(f"{f}: {lines}")
            except Exception as e:
                print(e)
                # append_if_not_exists(df_failures, [url, dir_name, full_path, f"failed reading file: {e}"])
                append_raw_csv("../dataset_features/clone_failures.csv", [url, dir_name, full_path, f"failed reading file: {e}"])
                lines= blank_lines= avg_line_len = None
                continue #want it to break and not include errored otu lines
            # print([url, dir_name, full_path, f, extn, lines, blank_lines, avg_line_len])
            try:
                 #DO NOT FORGET YOU DID THIS
                append_raw_csv("../dataset_features/files_raw.csv", [url, dir_name, full_path, f, extn, lines, blank_lines, avg_line_len])
                #append_if_not_exists(df, [url, dir_name, full_path, f, extn, lines, blank_lines, avg_line_len])
            except Exception as e:
                #I am loosing files right here
                append_raw_csv("../dataset_features/clone_failures.csv", [url, dir_name, full_path, f"failed appending to file: {e}"])
                print(e)
                df = [url, dir_name, full_path,f, extn, lines, blank_lines, avg_line_len]

            if 'requirements.txt' in f:
                #continue #REMEMBER THAT YOU DID THIS DO NOT FORGET DO NOT FORGET
                find_requirements(url, commit, dir_name, full_path) #IMPORTANT LINE IS HERE
            
            if extn == "py":
                print("found python")
                find_comments(url, commit, dir_name, full_path) #IMPORTANT LINE IS HERE
                find_imports(url, commit, dir_name, full_path)
                find_functions(url, commit, dir_name, full_path)
                find_classes(url, commit, dir_name, full_path)
                find_all_calls(url, commit, dir_name, full_path)

            # if '.py' in f:
            #     #print(str(root) +"/"+ f)
            #     python_files_list.append(str(str(root) +"/"+ f))
    return # df, df_failures




if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Interactively accept/reject NDJSON lines by viewing `body`.")
    p.add_argument("--file_name", type=str)
    p.add_argument("--url", type=str)
    p.add_argument("--commit", type=str)
    args = p.parse_args()
    print(args.file_name)
    files_finder(args.file_name, args.url, args.commit)
    # df, df_failures = files_finder(args.file_name, args.url, args.commit)
    # df.to_csv("../dataset_features/files_raw.csv")
    # df_failures.to_csv("../dataset_features/clone_failures.csv")