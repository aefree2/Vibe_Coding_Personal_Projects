import pandas as pd
import numpy as np
from pathlib import Path


DEFAULT_COLUMNS = {
    "source": "source",
    "vibe": "vibe_median",
    "human": "human_median",
    "significant": "significant",
    "direction": "direction",
    "effect_size": "effect_size",
}

HLINE = "__HLINE__"


def escape_latex(text) -> str:
    """Escape LaTeX special characters in a string."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


def format_value(value, is_percent: bool, decimals: int = 2) -> str:
    """Format a numeric value, optionally as an escaped LaTeX percentage."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "--"
    if isinstance(value, (int, float, np.integer, np.floating)):
        value = value * 100 if is_percent else value
        formatted = f"{value:.{decimals}f}"
        return f"{formatted}\\%" if is_percent else formatted
    return escape_latex(value)


def format_significant(before_correction, value) -> str:
    """Render a significance flag as a checkmark-style string."""
    if value <= 0.05:
        if round(value,2) ==0:
            return "\\textbf{ p< 0.01}"

        return "\\textbf{p=" + str(round(value,2)) + "}"
    elif before_correction == "False*":
            return "\\textit{p=" + str(round(value,2)) + "}"

    return "p="+str(round(value,2))

    
    # if isinstance(value, str):
    #     return escape_latex(value)
    # if value is None or (isinstance(value, float) and np.isnan(value)):
    #     return "--"
    # return "True" if bool(value) else "False"


def significance_value(row):
    """Return the p-value used for significance, regardless of dataset-specific column name."""
    for key in ("p_adj_bh", "p_adj", "p_value"):
        if key in row.index and row[key] is not None:
            value = row[key]
            if not pd.isna(value):
                return value
    return np.nan


def format_direction(value) -> str:
    """Render a direction flag as a string."""
    # if isinstance(value, str):
    #     return escape_latex(value)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "--"
    return "Vibe Coded" if value=="Vibecoding > SideProject"  else "Human-Written"

def format_effect_size(value, decimals: int = 2) -> str:
    """Format an effect size value."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "--"
    if isinstance(value, (int, float, np.integer, np.floating)):
        value = abs(value)
        if value < 0.15:
            return "Negligible"
        elif value < 0.33:
            return "Small"
        elif value < 0.47:
            return "Medium"
        else:
            return "Large"
        # return f"{value:.{decimals}f}"
    return escape_latex(value)


def make_latex_table(
    rows,
    columns: dict = None,
    decimals: int = 2,
    grey_hex: str = "EFEFEF",
    caption: str = None,
    label: str = None,
    shade_alternating: bool = True,
) -> str:
    """
    Build a LaTeX table with alternating grey/white rows.

    Parameters
    ----------
    rows : list
        Each element is [df_row, feature_name, is_percent], where
          df_row       : a pandas Series (one row of a dataframe)
          feature_name : str, the display name for the Feature column
          is_percent   : bool, whether the median values are percentages
    columns : dict, optional
        Maps logical fields to dataframe column names. Keys: source, vibe,
        human, significant, direction, effect_size.
    decimals : int
        Decimal places for numeric values.
    grey_hex : str
        Hex color (no #) for shaded rows.
    caption, label : str, optional
        Added to the table if provided.

    Returns
    -------
    str : the full LaTeX table.
    """
    cols = {**DEFAULT_COLUMNS, **(columns or {})}

    header = r"""\begin{table}[]
  \footnotesize
\begin{tabular}{lrrrrr}
\hline
\hline
\textbf{Feature}       & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Vibe Coded \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Human-written \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{Significant}} & \textbf{Direction} & \textbf{Effect Size} \\ \hline
"""
# & \textbf{Source}

    body_lines = []
    data_row_count = 0 
    for entry in rows:
        if entry is HLINE or entry == HLINE:
            body_lines.append(r"\hline")
            continue

        df_row, feature_name, is_percent = entry
        # Shade even-indexed rows grey, odd rows white (no command needed)
        # prefix = f"\\rowcolor[HTML]{{{grey_hex}}}\n" if i % 2 == 0 else ""
        if shade_alternating and data_row_count % 2 == 0:
            prefix = f"\\rowcolor[HTML]{{{grey_hex}}}\n"
        else:
            prefix = ""
        

        cells = [
            escape_latex(feature_name),
            # escape_latex(df_row[cols["source"]]),
            format_value(df_row.vibecoding_median, is_percent, decimals),
            format_value(df_row.sideproject_median, is_percent, decimals),
            format_significant(df_row.significant, df_row.p_adj_bh),
            format_direction_multiline(format_direction(df_row.effect_direction)),
            format_effect_size(df_row.effect_size, decimals),
        ]
        body_lines.append(prefix + " & ".join(cells) + r" \\")
        data_row_count = data_row_count + 1

    
    footer = "\\hline \\hline \n\\end{tabular}\n"
    if caption:
        footer += f"\\caption{{{escape_latex(caption)}}}\n"
    if label:
        footer += f"\\label{{{label}}}\n"
    footer += "\\end{table}"

    return header + "\n".join(body_lines) + footer


def make_table_comment_percent(
    rows,
    columns: dict = None,
    decimals: int = 2,
    grey_hex: str = "EFEFEF",
    caption: str = None,
    label: str = None,
    shade_alternating: bool = True,
) -> str:
    """
    Build a LaTeX table with alternating grey/white rows.

    Parameters
    ----------
    rows : list
        Each element is [df_row, feature_name, is_percent], where
          df_row       : a pandas Series (one row of a dataframe)
          feature_name : str, the display name for the Feature column
          is_percent   : bool, whether the median values are percentages
    columns : dict, optional
        Maps logical fields to dataframe column names. Keys: source, vibe,
        human, significant, direction, effect_size.
    decimals : int
        Decimal places for numeric values.
    grey_hex : str
        Hex color (no #) for shaded rows.
    caption, label : str, optional
        Added to the table if provided.

    Returns
    -------
    str : the full LaTeX table.
    """
    cols = {**DEFAULT_COLUMNS, **(columns or {})}

    header = r"""\begin{table}[]
  \footnotesize
\begin{tabular}{lrrrrr}
\hline
\hline
\textbf{Category}       & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}\% Vibe\\Coded\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}\%Human- \\ Written\end{tabular}}} & \multicolumn{1}{l}{\textbf{Significant}} & \textbf{Direction} & \textbf{Effect Size} \\ \hline
"""
# & \textbf{Source}

    body_lines = []
    data_row_count = 0 
    for entry in rows:
        if entry is HLINE or entry == HLINE:
            body_lines.append(r"\hline")
            continue

        df_row, feature_name, is_percent = entry
        # Shade even-indexed rows grey, odd rows white (no command needed)
        # prefix = f"\\rowcolor[HTML]{{{grey_hex}}}\n" if i % 2 == 0 else ""
        if shade_alternating and data_row_count % 2 == 0:
            prefix = f"\\rowcolor[HTML]{{{grey_hex}}}\n"
        else:
            prefix = ""
        

        cells = [
            escape_latex(feature_name),
            # escape_latex(df_row[cols["source"]]),
            format_value(df_row.vibe_rate, is_percent, decimals),
            format_value(df_row.side_rate, is_percent, decimals),
            format_significant(significance_value(df_row)),
            format_direction_multiline(format_direction(df_row.effect_direction)),
            format_effect_size(df_row.effect_size, decimals),
        ]
        body_lines.append(prefix + " & ".join(cells) + r" \\")
        data_row_count = data_row_count + 1

    
    footer = "\\hline \\hline \n\\end{tabular}\n"
    if caption:
        footer += f"\\caption{{{escape_latex(caption)}}}\n"
    if label:
        footer += f"\\label{{{label}}}\n"
    footer += "\\end{table}"

    return header + "\n".join(body_lines) + footer



def format_bool_sig(value, footnote: bool = False) -> str:
    """Format significance as TRUE/FALSE, with optional trailing asterisk."""
    if isinstance(value, str):
        return escape_latex(value)
    base = "TRUE" if bool(value) else "FALSE"
    return base + ("*" if footnote else "")


def wrap_multiline(text: str) -> str:
    """
    Wrap text in the tabular-cell-that-breaks-lines idiom used throughout
    these tables: \begin{tabular}[c]{@{}l@{}}line1 \\ line2\end{tabular}
    `text` may already contain literal '\\' to mark manual line breaks;
    otherwise it's placed on a single line.
    """
    return r"\begin{tabular}[c]{@{}l@{}}" + text + r"\end{tabular}"

DIRECTION_LINE_BREAKS = {
    "Vibe Coding": r"Vibe \\ Coding",
    "Human-Written": r"Human-\\ Written",
}


def format_direction_multiline(direction: str) -> str:
    """
    Return the direction string formatted with an explicit line break,
    wrapped in the multiline tabular-cell idiom. Falls back to a naive
    single-space split if the value isn't in the known lookup.
    """
    raw = str(direction)
    if raw in DIRECTION_LINE_BREAKS:
        return wrap_multiline(DIRECTION_LINE_BREAKS[raw])

    # fallback: split on first space (won't handle hyphenated words specially)
    return wrap_multiline(escape_latex(raw).replace(" ", r" \\ ", 1))


def make_scoped_metric_table(
    groups,
    columns: dict = None,
    decimals: int = 2,
    grey_hex: str = "EFEFEF",
    caption: str = None,
    label: str = None,
) -> str:
    """
    Build the scope/metric grouped LaTeX table (multirow + cellcolor style).

    Parameters
    ----------
    groups : list
        Each element describes one shaded group (e.g. "Project", "File"):
          {
            "scope": "Project",                  # multirow label, line breaks as literal '\\'
            "normalized_by": "Lines \\\\ in Project",  # shown once, centered vertically
            "metrics": [
                [df_row, metric_name, is_percent],  # one per line in the group
                [df_row, metric_name, is_percent],
                ...
            ]
          }
        Each metric's df_row needs the same fields as before (human_median,
        vibe_median, human_mean, vibe_mean, significant, direction,
        effect_size), configurable via `columns`.
    columns : dict, optional
        Maps logical fields to dataframe column names. Keys: human_median,
        vibe_median, human_mean, vibe_mean, significant, direction, effect_size.
    decimals : int
        Decimal places for numeric values.
    grey_hex : str
        Hex color (no #) for shaded rows.
    caption, label : str, optional

    Returns
    -------
    str : the full LaTeX table.
    """
    default_cols = {
        "human_median": "human_median",
        "vibe_median": "vibe_median",
        "human_mean": "human_mean",
        "vibe_mean": "vibe_mean",
        "significant": "significant",
        "direction": "direction",
        "effect_size": "effect_size",
    }
    cols = {**default_cols, **(columns or {})}

    header = r"""\begin{table}[]
  \footnotesize
\begin{tabular}{lllllllll}
\hline
\hline
\textbf{Scope}                                     & \textbf{Metric}                                                                                                                              & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Vibe\\Coded \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Human-\\Written \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Vibe\\Coded \\ Mean\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Human-\\Written \\ Mean\end{tabular}}} & \multicolumn{1}{l}{\textbf{Significant}} & \textbf{Direction}                                       & \textbf{Size} \\ \hline
"""
#& \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Normalized \\ By\end{tabular}}} 

    body_lines = []

    for group in groups:
        scope = group["scope"]
        # normalized_by = group.get("normalized_by", "")
        metrics = group["metrics"]
        n = len(metrics)

        for i, metric_entry in enumerate(metrics):
            if len(metric_entry) == 3:
                df_row, metric_name, is_percent = metric_entry
                footnote = False
            elif len(metric_entry) == 4:
                df_row, metric_name, is_percent, footnote_flag = metric_entry
                footnote = bool(footnote_flag)
            else:
                raise ValueError(
                    f"Each metric entry must have 3 or 4 values; got {len(metric_entry)}: {metric_entry}"
                )

            cells = []

            if i == 0:
                # Top row of the group: rowcolor + blank cellcolor'd Scope cell
                body_lines.append(f"\\rowcolor[HTML]{{{grey_hex}}} ")
                cells.append(f"\\cellcolor[HTML]{{{grey_hex}}}")
            else:
                # Last row of the group: multirow pulls the Scope label up
                # across all n rows of this group (negative offset = upward)
                cells.append(
                    f"\\multirow{{-{n}}}{{*}}{{\\cellcolor[HTML]{{{grey_hex}}}{escape_latex(scope)}}}"
                )

            cells.append((wrap_multiline(metric_name)))

            # Normalized-By column only appears once per group, on the first row,
            # and is left blank (spanned visually by \multirow-like convention) after
            # cells.append(wrap_multiline(normalized_by) if i == 0 else "")

            cells.append(format_value(df_row.vibecoding_median, is_percent, decimals))
            cells.append(format_value(df_row.sideproject_median, is_percent, decimals))

            cells.append(format_value(df_row.vibecoding_mean, is_percent, decimals))
            cells.append(format_value(df_row.sideproject_mean, is_percent, decimals))
            

            sig_val = df_row[cols["significant"]]
            cells.append(format_bool_sig(sig_val, footnote=footnote))

            cells.append(format_direction_multiline(format_direction(df_row.effect_direction)))
            # cells.append(wrap_multiline(escape_latex(df_row.effect_direction).replace(" ", " \\\\ ", 1)
            #               if "-" not in str(df_row.effect_direction) else escape_latex(df_row.effect_direction)))
            cells.append(format_effect_size(df_row.effect_size))

            line = " & ".join(cells) + r" \\"
            if i == n - 1:
                line += r" \hline"
            body_lines.append(line)

        # body_lines.append(r"\hline")

    footer = "\hline \\end{tabular}\n"
    if caption:
        footer += f"\\caption{{{escape_latex(caption)}}}\n"
    if label:
        footer += f"\\label{{{label}}}\n"
    footer += "\\end{table}"

    return header + "\n".join(body_lines) + "\n" + footer



def make_gen_python(df, df_file):
    table_rows = [
    [df.loc["n_files"], "Average Number of Python Files in Project", False],
    [df.loc["n_lines"], "Average Number of Python Lines in Project", False],

    # [df.loc["avg_file_length"], "Average File Length", False],
    [df_file.loc["n_lines"], "File Length", False],
    [df_file.loc["char_by_code"], "Average Line Length", False],

    # [df.loc["percent_code_lines"], "Percent Code Lines", True],
    # [df.loc["percent_comment_lines"], "Percent Comment Lines", True],
    # [df.loc["percent_blank_lines"], "Percent Blank Lines", True],

]

    # print(make_latex_table(table_rows, caption="Feature comparison", label="tab:features"))


    table_text = make_latex_table(
        table_rows,
        caption="Feature comparison",
        label="tab:features",
    )

    output_path = Path(__file__).resolve().parent / "latex_table.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_error_table(df):

    table_rows = [
        [df.loc["error"], "Error", True],
        [df.loc["refactor"], "Refactor", True],
        [df.loc["convention"], "Convention", True],
        [df.loc["warning"], "Warning", True],
        # [df.loc["info"], "Info", True],

  
    ]

    # print(make_latex_table(table_rows, caption="Feature comparison", label="tab:features"))


    table_text = make_latex_table(
        table_rows,
        caption="Error Messages Comparison. The values presented are the median chance that any line in a given project will generate a Pylint message of the given type. Human-written code is more likely to generate Pylint messages of every type. Specific descriptions of each message type can be found in section 3.2.3.",
        label="tab:error",
    )

    output_path = Path(__file__).resolve().parent / "latex_error.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_import_table(df, df_file):
    table_rows = [
    [df_file.loc["n_imports"], "Imports per File", False],
    [df.loc["unique_imports_per_project"], "Average Unique Imports per File", False],
    [df_file.loc["n_internal_imports"], "Within-Project Imports", False],
    # [df_file.loc["n_external_imports"], "External Imports", False],
    ]
    table_text = make_latex_table(
    table_rows,
    caption="Import Comparison",
    label="tab:imports",
    )
    output_path = Path(__file__).resolve().parent / "latex_imports.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_classes_fns_table(df):
    table_rows = [
    [df.loc["n_functions"], "Functions Defined per Code Line", False],
    [df.loc["class_count"], "Classes Defined per Code Line", False],
    [df.loc["n_fn_called"], "Project-Defined Functions Called per Code Line", False],

    [df.loc["n_total_calls"], "Total Functions Called per Code Line", False],
    [df.loc["n_fn_called"], "Project-Defined Functions Called per Code Line", False],
    [df.loc["n_out_of_project_calls"], "Out-of-Project Functions Called per Code Line", False],
    # "__HLINE__",

    # [df_file.loc["n_functions_by_code"], "Functions Defined per Code Line(f)", False],
    # [df_file.loc["class_count_by_code"], "Classes Defined per Code Line(f)", False],
    # [df_file.loc["n_fn_called_by_code"], "Project-Defined Functions Called per Code Line(f)", False],

    # [df_file.loc["n_calls_by_code"], "Total Functions Called per Code Line(f)", False],
    # [df_file.loc["n_fn_called_by_code"], "Project-Defined Functions Called per Code Line(f)", False],
    # [df_file.loc["n_external_fn_calls_by_code"], "External Functions Called per Code Line(f)", False]



    

    ]
    table_text = make_latex_table(
    table_rows,
    caption="Class and Function Comparison",
    label="tab:classes_fns",
    )
    output_path = Path(__file__).resolve().parent / "latex_classes_fns.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_class_table(df_class):
    table_rows = [
        [df_class.loc["line_count"], "Number of Lines", False],
        # [df_class.loc["n_characters"], "Average Line Length", False],
        [df_class.loc["n_instance_vars_raw"], "Number of Instance Variables", False],
        [df_class.loc["n_fns_raw"], "Number of Methods", False],
        [df_class.loc["n_function_calls"], "Function Calls per Line", False],
        "__HLINE__",

        # [df_class.loc["percent_code"], "Percent Code Lines", True],
        # [df_class.loc["percent_blank"], "Percent Blank Lines", True],
        # "__HLINE__",


        # #Child Class Section
        # [df_class.loc["is_child_class"], "Percentage of Total Classes That are Child Classes", True],
        # [df_class.loc["n_child_classes_by_total_classes"], "Percentage of Total Classes That are Child of given Class", True],
        # "__HLINE__",

        # #Invocations Section 
        # [df_class.loc["n_times_invoked_by_all_lines"], "Percentage of Lines that Invoke Class", True],
        # [df_class.loc["n_times_imported_by_files"], "Percentage of Files that Import Class", True],
 
        ]
    table_text = make_latex_table(
        table_rows,
        caption="Class level metrics. Human-written classes are more hierarchical, vibe coded classes are used more often.",
        label="tab:Class",
        )
    output_path = Path(__file__).resolve().parent / "latex_class.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_fn_table(df_fn):
    table_rows = [
    [df_fn.loc["n_code_lines"], "Number of Code Lines", False],
    # [df_fn.loc["n_characters_total_by_line"], "Average Line Length", False],
    [df_fn.loc["n_args"], "Number of Arguments", False],
    [df_fn.loc["n_called_by_line"], "Function Calls per Line", False],
    [df_fn.loc["n_vars_by_line"], "Variables Defined Per Line", False],
    [df_fn.loc["cyclomatic_complexity"], "Cyclomatic Complexity", False],
    "__HLINE__",



    # [df_fn.loc["percent_code"], "Percent Code Lines", True],
    # [df_fn.loc["percent_blank"], "Percent Blank Lines", True],
    # "__HLINE__",

    # #Calls Section 
    # [df_fn.loc["n_total_calls_by_total"], "Percentage of Lines that Invoke Function", True],
    # [df_fn.loc["n_times_imported_by_file"], "Percentage of Files that Import Function", True],

    ]
    table_text = make_latex_table(
    table_rows,
    caption="Vibe Coded functions are longer with more variables, that is more complex.  Human-written functions are used more often, and have more arguments.",
    label="tab:function-py-met",
    )
    output_path = Path(__file__).resolve().parent / "latex_fn.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_comments(df, df_file, df_class, df_fn):
    groups = [
    {
        "scope": "Project",
        "normalized_by": "Lines \\\\ in Project",
        "metrics": [
            [df.loc["percent_comment_lines"], "Percent Comments", True],
            [df.loc["avg_lines_in_comment"], "Average Lines \\\\ per Comment", False, True],
        ],
    },
    {
        "scope": "File",
        "normalized_by": "Lines \\\\ in File",
        "metrics": [
            [df_file.loc["percent_comments"], "Percent Comments", True],
            [df_file.loc["avg_lines_in_comment"], "Average Lines \\\\ per Comment", False, True],
        ],
    },

    {
        "scope": "Class",
        "normalized_by": "Lines \\\\ in Class",
        "metrics": [
            [df_class.loc["percent_comments"], "Percent Comments", True],
            [df_class.loc["avg_lines_in_comment"], "Average Lines \\\\ per Comment", False, True],
        ],
    },
    {
        "scope": "Function",
        "normalized_by": "Lines \\\\ in Function",
        "metrics": [
            [df_fn.loc["percent_comments"], "Percent Comments", True],
            [df_fn.loc["avg_lines_in_comment"], "Average Lines \\\\ per Comment", False, True],
        ],
    },
]
    table_text = make_scoped_metric_table(groups, caption="Mean and median percentage of each scope that consist of comments. Mean and median number of lines per comment. Vibe coded projects have more comments, but human-written projects have longer comments.", label="tab:comments_percent")

    output_path = Path(__file__).resolve().parent / "latex_comments.txt"
    output_path.write_text(table_text, encoding="utf-8")

def make_comments_cat(df_comments):
    table_rows = [
    [df_comments.loc["Tool Use *"], "Tool Use", True],
    [df_comments.loc["Note to self"], "Note to Self", True],
    [df_comments.loc["Note to self"], "Note to Self", True],
    [df_comments.loc["Note to self"], "Note to Self", True],
    [df_comments.loc["Note to self"], "Note to Self", True],
    [df_comments.loc["Note to self"], "Note to Self", True]





    ]
    table_text = make_latex_table(
    table_rows,
    caption="Percentage of comments by category. Human-written projects have more qualitative comments and to-do items, showing the mental models behind the coding process. Vibe coded projects have more direct explainers, showing a focus on the code itself. Significance is calculated using proportions-z test and effect size using Cohens H. ",
    label="tab:comments",
    )
    output_path = Path(__file__).resolve().parent / "latex_comments_cat.txt"
    output_path.write_text(table_text, encoding="utf-8")
    

# ---------------- Example usage ----------------
if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent

    # df = pd.DataFrame(
    #     {
    #         "source": ["GitHub", "GitHub", "StackOverflow"],
    #         "vibe_median": [12.4, 0.83, 45.1],
    #         "human_median": [9.8, 0.91, 30.2],
    #         "significant": [True, False, True],
    #         "direction": ["Higher", "Lower", "Higher"],
    #         "effect_size": [0.42, 0.05, 0.61],
    #     }
    # )
    df = pd.read_csv(data_dir / "proj_level_results_py.csv")
    df = df.set_index("feature")
    df["effect_size"] = df["size"]
    df["p_adj_bh"] = df["p_adj"]
    df["significant"] = np.select(
    [
        df["p_adj"] < 0.05,
        (df["p_adj"] > 0.05) & (df["p_value"] < 0.05),
    ],
    [
        True,
        "False*",
    ],
    default=False,
)
    # print(df.columns)
    df_file = pd.read_csv(data_dir / "file_level_py.csv")
    # print(df_file.metric)
    
    df_file = df_file.set_index("metric")
    df_file["vibecoding_median"] = df_file["Vibecoding_median"]
    df_file["sideproject_median"] = df_file["SideProject_median"]
    df_file["vibecoding_mean"] = df_file["Vibecoding_mean"]
    df_file["sideproject_mean"] = df_file["SideProject_mean"]
    df_file["significant"] = np.select(
    [
        df_file["p_adj_bh"] < 0.05,
        (df_file["p_adj_bh"] > 0.05) & (df_file["p_value"] < 0.05),
    ],
    [
        True,
        "False*",
    ],
    default=False,
)
    df_file["effect_size"] = df_file["size"]
    print(df_file.size)


    #Error Messages Table
    make_error_table(df)


    #First Table

    make_gen_python(df, df_file)



    #Imports Table

    make_import_table(df, df_file)



    #Class & FN Table
    make_classes_fns_table(df)
    ## CLASSES

    df_class = pd.read_csv(data_dir / "class_level_py.csv")
    df_class= df_class.set_index("metric")
    df_class["effect_size"] = df_class["size"]
    df_class["significant"] = np.select([df_class["p_adj_bh"] < 0.05, (df_class["p_adj_bh"] > 0.05) & (df_class["p_value"] < 0.05), ], [True,"False*",], default=False,)
    df_class["vibecoding_median"] = df_class["Vibecoding_median"]
    df_class["sideproject_median"] = df_class["SideProject_median"]
    df_class["vibecoding_mean"] = df_class["Vibecoding_mean"]
    df_class["sideproject_mean"] = df_class["SideProject_mean"]

    make_class_table(df_class)


    ## Functions

    df_fn = pd.read_csv(data_dir / "fn_level_py.csv")
    df_fn= df_fn.set_index("metric")
    df_fn["effect_size"] = df_fn["size"]
    df_fn["significant"] = np.select([df_fn["p_adj_bh"] < 0.05, (df_fn["p_adj_bh"] > 0.05) & (df_fn["p_value"] < 0.05), ], [True,"False*",], default=False,)
    df_fn["vibecoding_median"] = df_fn["Vibecoding_median"]
    df_fn["sideproject_median"] = df_fn["SideProject_median"]
    df_fn["vibecoding_mean"] = df_fn["Vibecoding_mean"]
    df_fn["sideproject_mean"] = df_fn["SideProject_mean"]
    make_fn_table(df_fn)

    # comments
    make_comments(df, df_file, df_class, df_fn)

    # Comments Category
    df_comments = pd.read_csv("../../comments/all_comments_results.csv")
    df_comments = df_comments.set_index("category")
    # make_comments_cat(df_comments)

    




    
    

