## The one in which I make figures for language

""" 
Design I want
        Feature
Lang    Number of files per project
        File Length
    

"""


import pandas as pd
import numpy as np
from pathlib import Path
from make_figures import format_effect_size, format_direction

def get_before_sig(p_value):
    if p_value < 0.05:
        return True
    return False


def format_p_value(
    p_raw,
    p_adjusted,
    alpha: float = 0.05,
    decimals: int = 3,
    display: str = "adjusted",  # "adjusted" or "raw"
) -> str:
    """
    Format a p-value as p=x.xxx, or p<0.001 if it rounds to 0.000.
    Bolds the value if p_adjusted < alpha (significant after BH correction).
    Italicizes it if p_raw < alpha but p_adjusted >= alpha (significant only
    before correction). Leaves it plain otherwise.

    `display` controls which value (raw or adjusted) is actually printed.
    """
    if p_raw is None or p_adjusted is None:
        return "--"
    if (isinstance(p_raw, float) and np.isnan(p_raw)) or (isinstance(p_adjusted, float) and np.isnan(p_adjusted)):
        return "--"

    shown = p_adjusted if display == "adjusted" else p_raw
    threshold = 10 ** (-decimals)
    if shown < threshold:
        text = f"p{{\\textless}}{threshold:.{decimals}f}"
    else:
        text = f"p={shown:.{decimals}f}"

    if p_adjusted < alpha:
        return f"\\textbf{{{text}}}"
    elif p_raw < alpha:
        return f"\\textit{{{text}}}"
    return text


def make_extension_feature_table(
    groups,
    columns: dict = None,
    decimals: int = 2,
    p_decimals: int = 3,
    alpha: float = 0.05,
    p_display: str = "adjusted",
    grey_hex: str = "EFEFEF",
    caption: str = None,
    label: str = None,
) -> str:
    ...
    default_cols = {
        "vibe_median": "vibe_median",
        "human_median": "human_median",
        "vibe_mean": "vibe_mean",
        "human_mean": "human_mean",
        "p_raw": "p_raw",
        "p_adjusted": "p_adjusted",
        "direction": "direction",
        "effect_size": "effect_size",
    }
    cols = {**default_cols, **(columns or {})}
    ...

    # inside the per-feature loop:
    cells.append(
        format_p_value(
            feat[cols["p_raw"]],
            feat[cols["p_adjusted"]],
            alpha=alpha,
            decimals=p_decimals,
            display=p_display,
        )
    )



import pandas as pd
import numpy as np


def escape_latex(text) -> str:
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
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "--"
    formatted = f"{value:.{decimals}f}"
    return f"{formatted}\\%" if is_percent else formatted


def format_p_value(p_value, significant: bool, significant_uncorrected: bool, decimals: int = 3) -> str:
    """
    Format a p-value as p=x.xxx or p<0.001 (for values rounding to 0),
    bolding truly significant values and italicizing values that were
    only significant before correction.
    """
    if p_value is None or (isinstance(p_value, float) and np.isnan(p_value)):
        return "--"

    threshold = 10 ** (-decimals)
    if p_value < threshold:
        text = f"p\\textless{threshold:.{decimals}f}"
    else:
        text = f"p={p_value:.{decimals}f}"

    if significant:
        return f"\\textbf{{{text}}}"
    elif significant_uncorrected:
        return f"\\textit{{{text}}}"
    return text


def format_direction_multiline(direction: str) -> str:
    """Two-line direction labels, matching the earlier scoped table's style."""
    lookup = {
        "Vibe Coding": r"Vibe \\ Coding",
        "Vibe Coded": r"Vibe \\ Coded",
        "Human-Written": r"Human-\\ Written",
    }
    raw = str(direction)
    if raw in lookup:
        return r"\begin{tabular}[c]{@{}l@{}}" + lookup[raw] + r"\end{tabular}"
    return escape_latex(raw)


def make_extension_feature_table(
    groups,
    columns: dict = None,
    decimals: int = 2,
    p_decimals: int = 3,
    grey_hex: str = "EFEFEF",
    caption: str = None,
    label: str = None,
) -> str:
    """
    Build the Extension/Feature grouped LaTeX table (multirow + cellcolor,
    with p-value significance formatting).

    Parameters
    ----------
    groups : list
        Each element is:
          {
            "extension": "Lang",     # multirow label spanning this group
            "features": [
                {
                    "name": "Number of files per project",
                    "is_percent": False,
                    "vibe_median": ..., "human_median": ...,
                    "vibe_mean": ..., "human_mean": ...,
                    "p_value": 0.0004,
                    "significant": True,
                    "significant_uncorrected": False,
                    "direction": "Vibe Coded",
                    "effect_size": "Medium",
                },
                ...
            ]
          }
        Each feature dict's numeric keys are read directly (not via a
        dataframe row) for simplicity; if you have a dataframe row instead,
        pass it and set `columns` to map field names, and this function
        will do row[columns["vibe_median"]] etc. To keep this general, this
        implementation accepts either a dict or a pandas Series per feature,
        indexed the same way.
    columns : dict, optional
        Maps logical fields to your row's actual key/column names, if not
        using the default names shown above.
    decimals : int
        Decimal places for numeric (non-p-value) values.
    p_decimals : int
        Decimal places for p-values (and the `p<...` threshold).
    grey_hex : str
        Hex color (no #) for shaded rows.
    caption, label : str, optional

    Returns
    -------
    str : the full LaTeX table.
    """
    default_cols = {
        "vibe_median": "vibe_median",
        "human_median": "human_median",
        "vibe_mean": "vibe_mean",
        "human_mean": "human_mean",
        "p_value": "p_value",
        "significant": "significant",
        "significant_uncorrected": "significant_uncorrected",
        "direction": "direction",
        "effect_size": "effect_size",
    }
    cols = {**default_cols, **(columns or {})}

    header = r"""\begin{table}[]
  \footnotesize
\begin{tabular}{|clrrrrcll|}
\hline
\textbf{Extension}                              & \textbf{Feature}                        & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Vibe \\ Coded \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Human-\\Written \\ Median\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Vibe \\ Coded \\ Mean\end{tabular}}} & \multicolumn{1}{l}{\textbf{\begin{tabular}[c]{@{}l@{}}Human\\-Written \\ Mean\end{tabular}}} & \multicolumn{1}{l}{\textbf{Significant}} & \textbf{Direction}                    & \textbf{Size}                 \\ \hline
"""

    body_lines = []

    for group in groups:
        extension = group["extension"]
        features = group["features"]
        n = len(features)

        for i, feat in enumerate(features):
            cells = []

            if i == 0:
                body_lines.append(f"\\rowcolor[HTML]{{{grey_hex}}} ")
                cells.append(f"\\cellcolor[HTML]{{{grey_hex}}}")
            else:
                cells.append(
                    f"\\multirow{{-{n}}}{{*}}{{\\cellcolor[HTML]{{{grey_hex}}}{escape_latex(extension)}}}"
                )

            is_percent = feat[cols.get("is_percent", "is_percent")] if "is_percent" in feat else feat.get("is_percent", False)

            cells.append(feat["name"])
            cells.append(format_value(feat[cols["vibe_median"]], is_percent, decimals))
            cells.append(format_value(feat[cols["human_median"]], is_percent, decimals))
            cells.append(format_value(feat[cols["vibe_mean"]], is_percent, decimals))
            cells.append(format_value(feat[cols["human_mean"]], is_percent, decimals))
            cells.append(
                format_p_value(
                    feat[cols["p_value"]],
                    bool(feat[cols["significant"]]),
                    bool(feat[cols["significant_uncorrected"]]),
                    p_decimals,
                )
            )
            cells.append(format_direction_multiline(feat[cols["direction"]]))
            cells.append(escape_latex(feat[cols["effect_size"]]))

            line = " & ".join(cells) + r" \\"
            if i == n - 1:
                line += r" \hline"
            body_lines.append(line)

    footer = "\\end{tabular}\n"
    if caption:
        footer += f"\\caption{{{escape_latex(caption)}}}\n"
    if label:
        footer += f"\\label{{{label}}}\n"
    footer += "\\end{table}"

    return header + "\n".join(body_lines) + "\n" + footer



def get_values_from_row(df_row):
    return {
        "name": "\\begin{tabular}[c]{@{}l@{}}Number of Files\\\\ per Project\end{tabular}",
        "is_percent": False,
        "vibe_median": df_row.vibecoding_median, "human_median": df_row.sideproject_median,
        "vibe_mean":df_row.vibecoding_mean, "human_mean": df_row.sideproject_mean,
        "p_value": df_row.p_adj, "significant": df_row.significant, "significant_uncorrected": get_before_sig(df_row.p_value),
        "direction": format_direction(str(df_row.effect_direction)), "effect_size": format_effect_size(df_row.effect_size),
            }

def get_file_values_from_row(df_row):
    return {
        "name": "File Length (Lines)",
        "is_percent": False,
        "vibe_median": df_row.vibecoding_median, "human_median": df_row.sideproject_median,
        "vibe_mean": df_row.vibecoding_mean, "human_mean": df_row.sideproject_mean,
        "p_value": df_row.p_adj, "significant": df_row.significant, "significant_uncorrected":  get_before_sig(df_row.p_value),
        "direction": format_direction(str(df_row.effect_direction)), "effect_size": format_effect_size(df_row.effect_size),
    }

# ---------------- Example usage ----------------
if __name__ == "__main__":

    df_lang = pd.read_csv("../proj_level_results.csv")
    df_lang = df_lang.set_index("feature")
    df_lang["effect_size"] = df_lang["size"]

    df_file = pd.read_csv("../file_level.csv")
    df_file["feature"] = df_file["extn"] + "_" + df_file["metric"]
    df_file = df_file.set_index("feature")
    df_file["effect_size"] = df_file["size"]
    #Languages, Markdown, JavaScript, TypeScript,Python, Shell, Go,C#, Java, SCSS
    groups = [
        {
            "extension": "Markdown",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_md"]),
                get_file_values_from_row(df_file.loc["md_n_lines"])
            ],
        },
        {
            "extension": "JavaScript",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_js"]),
                get_file_values_from_row(df_file.loc["js_n_lines"])
            ],
        },
        {
            "extension": "TypeScript",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_ts"]),
                get_file_values_from_row(df_file.loc["ts_n_lines"])
            ],
        },
        {
            "extension": "Python",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_py"]),
                get_file_values_from_row(df_file.loc["py_n_lines"])
            ],
        },
        {
            "extension": "Shell",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_sh"]),
                get_file_values_from_row(df_file.loc["sh_n_lines"])
            ],
        },
        {
            "extension": "Go",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_go"]),
                get_file_values_from_row(df_file.loc["go_n_lines"])
            ],
        },
        {
            "extension": "C#",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_cs"]),
                get_file_values_from_row(df_file.loc["cs_n_lines"])
            ],
        },
        {
            "extension": "Java",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_java"]),
                get_file_values_from_row(df_file.loc["java_n_lines"])
            ],
        },
        {
            "extension": "SCSS",
            "features": [
                get_values_from_row(df_lang.loc["n_files_ext_scss"]),
                get_file_values_from_row(df_file.loc["scss_n_lines"])
            ],
        },
    ]
    table_text = make_extension_feature_table(groups, caption="Files per project and file length by language.", label="tab:lang-features")
    print(make_extension_feature_table(groups, caption="Files per project and file length by language.", label="tab:lang-features"))

    output_path = Path(__file__).resolve().parent / "latex_files_per_project.txt"
    output_path.write_text(table_text, encoding="utf-8")

