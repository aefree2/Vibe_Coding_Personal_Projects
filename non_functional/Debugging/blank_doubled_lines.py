import pandas as pd
import re

def get_testing_subset(df):
    sample_df = df.sample(50)
    sample_df.to_csv("sample_projects.csv")

def first_time_setup():
    fn_df = pd.read_csv("../../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])
    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'n_args', 'n_args': 'line_count','line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    fn_df.drop_duplicates(inplace=True)
    get_testing_subset(fn_df)

def second_time():
    fn_df = pd.read_csv("sample_projects.csv")
    return fn_df


def count_blank_lines(function_code):
    if not isinstance(function_code, str):
        return 0

    return sum(
        1 for line in function_code.splitlines()
        if not line.strip()
    )

def link_maker(df):
    df["link"] = df["url"] + "/blob/" + df["commit"] + "/" + df["file_path"].str.split("/", n=1).str[-1]
    return df

def deduplicate_doubles(fn_code):
    text = re.sub(r"\n\n", "\n", fn_code)
    return text

def replace_doubled_newlines(df):
    df["new_code"] = df["fn_code"].apply(deduplicate_doubles)
    return df

# correct_total_line_count=[1, 15, ]
# correct_blank_lines=[0, 2 , ]

def count_function_lines(function_code):
    if not isinstance(function_code, str):
        return 0

    return len(function_code.splitlines())



if __name__ == "__main__":
    # first_time_setup()
    fn_df = second_time()
    fn_df["n_blank_lines"] = fn_df["fn_code"].apply(count_blank_lines)
    fn_df = link_maker(fn_df)
    fn_df = replace_doubled_newlines(fn_df)
    fn_df["new_blank_lines"] = fn_df["new_code"].apply(count_blank_lines)
    # print(fn_df["new_blank_lines"])
    fn_df["new_n_lines"] = fn_df["new_code"].apply(count_function_lines)
    print(fn_df["new_n_lines"])

    #fixed fn lines, just need to import into 


    # for row in fn_df:
    #     print(f"link {row.link}")
    # print(f"n blank lines {fn_df["n_blank_lines"]}")
    # print(f"n lines {fn_df["line_count"]}")

    # fn_df.to_csv("checking_items.csv")
    
    #get the testing subset