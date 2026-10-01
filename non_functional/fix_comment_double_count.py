import pandas as pd

def count_blank_comments(comment):
    if not isinstance(comment, str):
        return 0

    return sum(
        1 for line in comment.splitlines()
        if not line.strip()
    )

def fix_blank_comment_lines(df):
    # print(df.value_counts("type"))
    df.loc[df["type"] == "docstring", "blank_in_docstring"] = (
    df.loc[df["type"] == "docstring", "raw"]
      .apply(count_blank_comments)  
    )
    df["blank_in_docstring"] = (
    df["blank_in_docstring"]
    .fillna(0))
    print(df.value_counts("blank_in_docstring"))
    return df

def is_inline_comment(context, raw_comment):
    if not isinstance(context, str) or not isinstance(raw_comment, str):
        return 0

    raw_comment = raw_comment.strip()

    for line in context.splitlines():
        if raw_comment in line:
            before_comment = line.split(raw_comment, 1)[0]

            # If something other than whitespace comes before the comment,
            # it is at the end of a code line.
            if before_comment.strip():
                return 1

            # Comment is on its own line
            return 0

    # Comment was not found in the context
    return 0

def fix_code_comment_lines(df):
    mask = df["type"] == "comment"
    df.loc[mask, "at_end_of_code_line"] =  df.loc[mask].apply( lambda row: is_inline_comment(
        row["comments"],
        row["raw"]
    ),axis=1) 
    df["at_end_of_code_line"] = (
    df["at_end_of_code_line"]
    .fillna(0)
)
    return df
        
    # print(df.value_counts("at_end_of_code_line"))


if __name__ == "__main__":
    colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw"] 
    comments = pd.read_csv("../dataset_features/comments.csv", names=colnames, header=None)
    comments= fix_blank_comment_lines(comments)
    comments= fix_code_comment_lines(comments)
    comments.to_csv("../dataset_features/comments_revised.csv")
    # comments[[
    #     "n_line_comments",
    #     "line_comment_lines",
    #     "n_block_comments",
    #     "block_comment_lines",
    #     "block_comment_blank_line",
    #     "double_count_lines"
    #     ]] = comments["raw"].apply(count_comments)
