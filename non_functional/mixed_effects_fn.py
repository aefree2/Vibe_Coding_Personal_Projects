import pandas as pd
# import researchpy as rp
# import statsmodels.api as sm
# import scipy.stats as stats
# import statsmodels.formula.api as smf
# import gpboost as gpb
import numpy as np
# from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
# from sklearn.preprocessing import StandardScaler
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
from ast import literal_eval
import re
import ast
import tokenize
from scipy.stats import chi2_contingency, fisher_exact
from pathlib import Path

from radon.complexity import cc_visit


import ast
import io
import tokenize
import pandas as pd

# from mixed_effects_class import count_line_comments, count_comments
# from mixed_effects_proj_py import comment_stats

def count_blank_lines(function_code):
    if not isinstance(function_code, str):
        return 0

    return sum(
        1 for line in function_code.splitlines()
        if not line.strip()
    )

def count_characters(function_code):
    if not isinstance(function_code, str):
        return 0

    return len(function_code)

def comment_stats(row):
    raw = str(row["raw"])

    return pd.Series({
        "comment_kind": (
            "line"
            if row["type"] == "comment"
            else "block"
        ),
        "comment_n_lines": len(raw.splitlines())
    })





def normalize_module_name(x):
    if pd.isna(x):
        return ""

    x = str(x).strip()
    x = x.replace("/", ".").replace("\\", ".")

    if x.endswith(".py"):
        x = x[:-3]

    return x.strip(".")


def module_from_file_path(path):
    return normalize_module_name(str(path))


def module_file_name(module):
    module = normalize_module_name(module)
    return module.split(".")[-1] if module else ""


def parse_imports_cell(imports):
    """
    Handles imports stored as:
      {'os', 're', 'utils'}
      {'utils': ['helper', 'parse']}
      "{'os', 're', 'utils': ['helper']}"  # if stored as string
    """

    if imports is None or (isinstance(imports, float) and pd.isna(imports)):
        return []

    if isinstance(imports, str):
        try:
            imports = ast.literal_eval(imports)
        except Exception:
            return []

    parsed = []

    if isinstance(imports, set):
        for item in imports:
            parsed.append({
                "import_module": normalize_module_name(item),
                "import_name": None,
                "import_type": "module",
            })

    elif isinstance(imports, dict):
        for module, names in imports.items():
            module = normalize_module_name(module)

            if names is None:
                parsed.append({
                    "import_module": module,
                    "import_name": None,
                    "import_type": "module",
                })
            else:
                for name in names:
                    parsed.append({
                        "import_module": module,
                        "import_name": str(name),
                        "import_type": "from",
                    })

    elif isinstance(imports, list):
        for item in imports:
            parsed.append({
                "import_module": normalize_module_name(item),
                "import_name": None,
                "import_type": "module",
            })

    return parsed

def add_function_call_counts_with_imports(
    functions_df,
    calls_df,
    imports_df,
    project_col="url",
    function_col="fn_name",
    calls_col="calls",
    file_col="file_path",
    imports_col="imports",
):
    
    # functions_df.origin_class.fillna("NaN", inplace=True)
    functions_df.fillna({"origin_class": "NaN"}, inplace=True)
    functions = functions_df.copy()
    calls = calls_df.copy()
    imports = imports_df.copy()
    # print(f" function columns: {functions.columns}")

    functions["function_module"] = functions[file_col].apply(module_from_file_path)
    functions["function_module_file"] = functions["function_module"].apply(module_file_name)
    # print(functions.shape)

    

    # -------------------------
    # 1. Make calls long
    # -------------------------
    call_rows = []

    for _, row in calls.iterrows():
        # print(_)
        # print(extract_call_names(row[calls_col]))
        mod_names, call_names = extract_call_names(row[calls_col])
        # print(mod_names)
        # print(call_names)
        for mod_name, call_name in zip(mod_names, call_names):
            call_rows.append({
                project_col: row[project_col],
                file_col: row[file_col],
                "mod_name": mod_name,
                "call_name": call_name,
            })

    calls_long = pd.DataFrame(call_rows)
    # print(calls_long[calls_long.file_path == "Anubis/theia/autograde/autograde/exercise.py"])

    result = functions.copy()

    if calls_long.empty:
        result["n_times_called"] = 0
        return result

    # -------------------------
    # 2. Same-file matches
    # -------------------------
    same_file_matches = calls_long.merge(
        functions,
        left_on=[project_col, file_col, "call_name"],
        right_on=[project_col, file_col,function_col],
        how="inner",
    ) # assuming that there is only one function with the same name per file (see graph for why that is not true)
    

    same_file_matches["match_type"] = "same_file"
    same_file_matches["called_in_file"] = same_file_matches[file_col]
    same_file_matches.to_csv("test_same_file_call.csv")
    # print(same_file_matches.shape)

    

    left_keys = [project_col, file_col, "call_name"]
    right_keys = [project_col, file_col, function_col]

    # print(calls_long.duplicated(left_keys).sum())
    # print(functions.duplicated(right_keys).sum())

    # -------------------------
    # 3. Build imports_long
    # -------------------------
    
    imports_long = functions.explode("import_locations")
    imports_long.fillna({'origin_class': "NaN", 'import_locations': 'NaN'}, inplace=True)
    # print(functions_df.origin_class) 
    # print(imports_long.origin_class)

    other_file_matches = calls_long.merge(
        imports_long,
        left_on=[project_col, file_col, "mod_name", "call_name"],
        right_on=[project_col, "import_locations", "origin_class", function_col],
        how="inner",
        suffixes=("_fn", "_call"),
    ) #fixed the problem on the other side, so it will not catch self.__whatever___
    # all_matches = same_file_matches
    # print("other files")
    other_file_matches["match_type"] = "on_import"
    other_file_matches["called_in_file"] = other_file_matches[f"{file_col}_fn"]
    # print(other_file_matches.head())
    other_file_matches.rename(columns={"file_path_call": file_col}, inplace=True)

    all_matches = pd.concat([same_file_matches, other_file_matches])
    # print(all_matches.shape)
    # all_matches.rename(columns={"file_path_fn": file_col}, inplace=True)

    all_matches.to_csv("test_same_file_call.csv")
    # print(all_matches[all_matches.match_type == ])
    # print(all_matches.match_type.value_counts())
    


    # -------------------------
    # 6. Count matched calls
    # -------------------------
    counts = (
        all_matches.groupby([project_col, file_col, function_col]).size()
        .reset_index(name="n_times_called")
    )

    # counts = (
    # all_matches
    # .groupby([project_col, file_col, function_col, "match_type"])
    # .agg(
    #     import_locations=("import_loc", list)
    # )
    # .size()
    # .unstack("match_type", fill_value=0)
    # .rename(columns={
    #     "same_file": "n_same_file_calls",
    #     "on_import": "n_imported_calls",
    # })
    # .reset_index()
# )
    counts = (
        all_matches
        .groupby([project_col, file_col, function_col])
        .agg(
            called_in_files=("called_in_file", lambda x: sorted(set(x))),
            n_same_file_calls=("match_type", lambda x: (x == "same_file").sum()),
            n_imported_calls=("match_type", lambda x: (x == "on_import").sum()),
        )
        .reset_index()
    )
    print(counts)

    # print(counts.shape)

    result = functions.merge(
        counts,
        on=[project_col, file_col, function_col],
        how="left",
    )
    # print(result.head())

    # result["n_times_called"] = (
    #     result["n_times_called"]
    #     .fillna(0)
    #     .astype(int)
    # )

    result["n_same_file_calls"] = (
    result["n_same_file_calls"]
    .fillna(0)
    .astype(int)
)

    result["n_imported_calls"] = (
    result["n_imported_calls"]
    .fillna(0)
    .astype(int)
)

    return result


def add_function_call_counts_same_file(
    functions_df,
    calls_df,
    project_col="project",
    function_col="fn_name",
    calls_col="calls",
    file_col="file_path",
):
    rows = []

    for _, row in calls_df.iterrows():
        project = row[project_col]
        caller_file = row[file_col]

        for call_name in extract_call_names(row[calls_col]):
            rows.append({
                project_col: project,
                file_col: caller_file,
                "call_name": call_name,
            })

    calls_long = pd.DataFrame(rows)

    result = functions_df.copy()

    if calls_long.empty:
        result["n_times_called"] = 0
        return result

    matches = calls_long.merge(
        functions_df,
        left_on=[project_col, file_col, "call_name"],
        right_on=[project_col, file_col, function_col],
        how="inner",
    )

    counts = (
        matches
        .groupby([project_col, file_col, function_col])
        .size()
        .reset_index(name="n_times_called")
    )

    result = result.merge(
        counts,
        on=[project_col, file_col, function_col],
        how="left",
    )

    result["n_times_called"] = (
        result["n_times_called"]
        .fillna(0)
        .astype(int)
    )

    return result

def extract_call_names(calls):
    if calls is None:
        # print("None")
        return [], []

    if isinstance(calls, str):
        try:
            calls = ast.literal_eval(calls)
        except Exception:
            # print(Exception)
            calls = [calls]

    if not isinstance(calls, (list, set, tuple)):
        # print("None")
        return [], []

    names = []
    cl = []

    for call in calls:
        # print("in calls")
        call = str(call).strip()
        match_class = "NaN"
        match = re.match(r"([A-Za-z_][\w\.]*)\s*\(", call)
        if match:
            # names.append(match.group(1))
        # raw_match = re.match(r"^([A-Za-z_][\w\.]*)\s*\(", call)
        # print(raw_match)
            if "." in match.group(1):
                # print(call)
                # print(match.group(1))
                # print("." in match.group(1))
                calls_list = re.split(r"\.", match.group(1))
                # print(calls_list)
                # if(len(calls_list)>2):
                    # print("PROBLEM")

                # match_class = re.match(r"^([A-Za-z_][\w\.]*)\s*\.", call)
                # match = re.match(r"\.([A-Za-z_][\w\.]*)\s*\(", call)
                # print(f"matched class: {match_class.group(1)}")
                # print(f"matched extn: {match}")
                cl.append(calls_list[-2])
                names.append(calls_list[-1])
        

            elif match:
                names.append(match.group(1))
                cl.append(match_class)

    return cl, names

def normalize_imports(imports):
    """
    Converts one imports cell into rows of:
    import_module, import_symbol

    import models              -> import_module='models', import_symbol=None
    from models import Exercise -> import_module='models', import_symbol='Exercise'
    """

    rows = []

    if imports is None:
        return rows

    if isinstance(imports, str):
        try:
            imports = ast.literal_eval(imports)
        except Exception:
            imports = {imports}

    if isinstance(imports, dict):
        imports = [imports]

    if not isinstance(imports, (set, list, tuple)):
        return rows

    for item in imports:
        if isinstance(item, dict):
            for module, symbols in item.items():
                if isinstance(symbols, str):
                    symbols = [symbols]

                for symbol in symbols:
                    rows.append({
                        "import_module": str(module),
                        "import_symbol": str(symbol)
                    })

        elif isinstance(item, str):
            # Handles strings like "flask: ['current_app']"
            if ":" in item and "[" in item and "]" in item:
                module, symbols_txt = item.split(":", 1)

                try:
                    symbols = ast.literal_eval(symbols_txt.strip())
                    if isinstance(symbols, str):
                        symbols = [symbols]

                    for symbol in symbols:
                        rows.append({
                            "import_module": module.strip(),
                            "import_symbol": str(symbol)
                        })

                except Exception:
                    rows.append({
                        "import_module": item,
                        "import_symbol": None
                    })

            # Handles normal module imports like "os", "models", "autograde.models"
            else:
                rows.append({
                    "import_module": item,
                    "import_symbol": None
                })

    return rows

def make_imports_long(imports_df, project_col="url", imports_col="imports"):
    rows = []

    for _, row in imports_df.iterrows():
        project = row[project_col]
        imports = normalize_imports(row[imports_col])

        for imp in imports:
            rows.append({
                project_col: project,
                "import_loc": row["file_path"],
                "import_module": imp["import_module"],
                "import_symbol": imp["import_symbol"]
            })

    return pd.DataFrame(rows)


# def make_module_suffixes(module_path):
#     """
#     Example:
#     repo.vibe_core.mahamantra.kernel.phoenix

#     returns:
#     [
#       "repo.vibe_core.mahamantra.kernel.phoenix",
#       "vibe_core.mahamantra.kernel.phoenix",
#       "mahamantra.kernel.phoenix",
#       "kernel.phoenix",
#       "phoenix"
#     ]
#     """
#     parts = str(module_path).split(".")
#     return [".".join(parts[i:]) for i in range(len(parts))]


# def add_module_suffix_rows(classes, module_path_col="class_module_path"):
#     rows = []

#     for idx, row in classes.iterrows():
#         for suffix in make_module_suffixes(row[module_path_col]):
#             new_row = row.to_dict()
#             new_row["module_match_key"] = suffix
#             rows.append(new_row)

#     return pd.DataFrame(rows)

def normalize_module_path(file_path):
    path = str(file_path)

    path = path.replace("\\", "/")
    path = path.replace(".py", "")

    parts = [p for p in path.split("/") if p]

    # Drop common non-package prefixes
    drop_prefixes = {"src", "lib", "app"}

    # Also drop repo/project folder if present by allowing suffix matching later
    cleaned = ".".join(parts)

    return cleaned


def make_module_suffixes(module_path):
    parts = str(module_path).split(".")
    return [".".join(parts[i:]) for i in range(len(parts))]

def normalize_dotted_module(x):
    x = str(x)
    x = x.replace("\\", "/")
    x = x.replace("/", ".")
    x = x.replace(".py", "")
    x = x.strip(".")
    return x

def normalize_module(x):
    return (
        str(x)
        .replace("\\", "/")
        .replace("/", ".")
        .replace(".py", "")
        .strip(".")
    )

def module_matches_file(import_module, file_path):
    import_module = normalize_module(import_module)
    file_module = normalize_module(file_path)

    return (
        file_module.endswith(import_module)
        or import_module.endswith(file_module)
        or import_module == file_module.split(".")[-1]
    )

def final_module_name(x):
    return normalize_dotted_module(x).split(".")[-1]

#Sees how many times the module is imported
def make_matches (
    classes_df,
    imports_long,
    project_col="url",
    class_col="class_name",
    class_file_col="file_path",
    imports_col="imports",
    is_fn=False
):
    
    classes = classes_df.copy()
        # Normalize class module names
    classes["class_module_file"] = (
        classes[class_file_col]
        .apply(lambda p: Path(str(p)).stem)
    )
    classes["class_module_path"] = classes[class_file_col].apply(normalize_dotted_module)
    classes["class_module_file"] = classes["class_module_path"].str.split(".").str[-1]

    imports_long["import_module"] = imports_long["import_module"].apply(normalize_dotted_module)
    imports_long["import_module_file"] = imports_long["import_module"].str.split(".").str[-1]

    imports_long["import_module"] = imports_long["import_module"].astype(str)
    
    symbol_imports = imports_long[
    imports_long["import_symbol"].notna()
    ].copy()
    # print("long_imports")
    # print(imports_long.head())

    symbol_imports["import_module_file"] = (
        symbol_imports["import_module"].str.split(".").str[-1]
    )
    # print(symbol_imports)

    symbol_candidates = symbol_imports.merge(
        classes,
        left_on=[project_col, "import_symbol", "import_module_file"],
        right_on=[project_col, class_col, "class_module_file"],
        how="inner"
    )

    symbol_matches = symbol_candidates[
    symbol_candidates.apply(
        lambda row: module_matches_file(
            row["import_module"], 
            row[class_file_col]
        ),
        axis=1
    ) 
    ] #add what file the import is located in

 

    # print(f"symbol_matches: {len(symbol_matches)}")
    # print(symbol_matches.head())

      # Case 2: import module
    # Count all functions defined in that imported module/file
    # module_imports = imports_long[
    #     imports_long["import_symbol"].isna()
    # ]
    module_imports = imports_long[
    imports_long["import_symbol"].isna()
    ].copy()

    # First do a cheap merge only on final file name: shared_state == shared_state
    module_candidates = module_imports.merge(
        classes,
        left_on=[project_col, "import_module_file"],
        right_on=[project_col, "class_module_file"],
        how="inner"
    )

    # Then require full suffix compatibility:
    # hooks.shared_state matches project.backend.hooks.shared_state
    module_matches = module_candidates[
        module_candidates.apply(
            lambda row: (
                row["class_module_path"].endswith(row["import_module"])
                or row["import_module"].endswith(row["class_module_path"]) #consider updating these to be more robust
                or row["import_module"] == row["class_module_file"]
            ),
            axis=1
        )
    ]

    # print(f"module matches: {len(module_matches)}")
    # print(module_matches.head())
    # print("module matches:")
    # print(module_matches.columns)
    # print("symbol matches:")
    # print(symbol_candidates.columns)
    # all_matches = module_matches.merge(symbol_matches, on=[project_col, "import_module", "import_symbol", "import_module_file"], how="inner")
    
    all_matches = pd.concat(
    [symbol_matches, module_matches],
    ignore_index=True)

    if is_fn:
        class_candidates = symbol_imports.merge(
        classes,
        left_on=[project_col, "import_symbol", "import_module_file"],
        right_on=[project_col, "origin_class", "class_module_file"],
        how="inner"
        )

        class_matches = class_candidates[
            class_candidates.apply(
                lambda row: module_matches_file(
                    row["import_module"], 
                    row[class_file_col]
                ),
                axis=1
            ) ]
        all_matches = pd.concat(
        [all_matches, class_matches],
        ignore_index=True)


    # print(f"{len(all_matches)}")
    # print(all_matches.head())
    # print()
    # print(all_matches.iloc[1])

    # Optional: avoid duplicate matches from module_file and module_path matching same import
    all_matches = all_matches.drop_duplicates(
        subset=[
            project_col,
            "import_module",
            "import_symbol",
            class_file_col,
            class_col,
            "import_loc",
        ]
    )
    # print(f"all_matches: {all_matches.columns}")
    counts = (
        all_matches
        .groupby([project_col, class_file_col, class_col], as_index=False)
        .agg(
            n_times_imported=("import_loc", "size"),
            import_locations=("import_loc", list),
        )
    )


    result = classes_df.merge(
        counts,
        on=[project_col, class_file_col, class_col],
        how="left"
    )

    result["n_times_imported"] = (
        result["n_times_imported"]
        .fillna(0)
        .astype(int)
    )
    return result

def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    mask = (df_files["url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files

####### Comments #################


def normalize_code(code):
    if not isinstance(code, str):
        return ""

    # If code contains literal "\n", convert them to real newlines
    if "\\n" in code and "\n" not in code:
        code = code.encode("utf-8").decode("unicode_escape")

    return code

# def count_line_comments(code):
#     code = normalize_code(code)

#     n_comments = 0
#     comment_lines = 0
#     line_comment_doubles = 0
#     in_comment_block = False

#     for line in code.splitlines():
#         stripped = line.strip()

#         if "#" in stripped:
#             comment_lines += 1

#             # Check whether there is code before the comment
#             before_comment = stripped.split("#", 1)[0].strip()

#             if before_comment:
#                 line_comment_doubles += 1

#             if not in_comment_block:
#                 n_comments += 1
#                 in_comment_block = True
#         else:
#             in_comment_block = False

#     return n_comments, comment_lines, line_comment_doubles


# def count_comments(class_code):
#     n_line_comments, line_comment_lines, line_comment_doubles = count_line_comments(class_code)

#     n_block_comments = 0
#     block_comment_lines = 0
#     block_comment_blank_lines = 0

#     # Keep the original source lines so we can inspect
#     # the contents of each block comment
#     source_lines = class_code.splitlines()

#     try:
#         tree = ast.parse(class_code)

#         for node in ast.walk(tree):
#             if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
#                 if (
#                     node.body
#                     and isinstance(node.body[0], ast.Expr)
#                     and isinstance(node.body[0].value, ast.Constant)
#                     and isinstance(node.body[0].value.value, str)
#                 ):
#                     doc_node = node.body[0]

#                     start_line = doc_node.lineno
#                     end_line = getattr(
#                         doc_node,
#                         "end_lineno",
#                         doc_node.lineno
#                     )

#                     n_block_comments += 1

#                     block_comment_lines += (
#                         end_line - start_line + 1
#                     )

#                     # AST line numbers are 1-based,
#                     # while Python lists are 0-based
#                     comment_lines = source_lines[
#                         start_line - 1:end_line
#                     ]

#                     block_comment_blank_lines += sum(
#                         1 for line in comment_lines
#                         if not line.strip()
#                     )

#     except SyntaxError:
#         pass

#     return pd.Series({
#         "n_line_comments": n_line_comments,
#         "line_comment_lines": line_comment_lines,
#         "n_block_comments": n_block_comments,
#         "block_comment_lines": block_comment_lines,
#         "block_comment_blank_lines": block_comment_blank_lines,
#         "double_count_lines": line_comment_doubles
#     })





def count_comments(class_code):
    if not isinstance(class_code, str):
        return pd.Series({
            "n_line_comments": 0,
            "line_comment_lines": 0,
            "n_block_comments": 0,
            "block_comment_lines": 0,
            "block_comment_blank_lines": 0,
            "double_count_lines": 0
        })

    # --------------------------------------------------
    # 1. Find # comments using tokenize
    # --------------------------------------------------
    n_line_comments = 0
    line_comment_lines = 0
    line_comment_doubles = 0 #bug, needs to count line comment lines that also contain code

    comment_line_numbers = []

    previous_standalone_comment_line = None

    try:
        tokens = tokenize.generate_tokens(
            io.StringIO(class_code).readline
        )

        source_lines = class_code.splitlines()

        for token in tokens:
            if token.type == tokenize.COMMENT:

                line_number = token.start[0]
                line_comment_lines += 1
                comment_line_numbers.append(line_number)

                # Get everything before the # on this line
                source_line = source_lines[line_number - 1]
                before_comment = source_line[:token.start[1]]

                # ------------------------------------------
                # Standalone comment
                # ------------------------------------------
                if not before_comment.strip():

                    # Start a new comment only if this isn't
                    # directly after another standalone comment
                    if (
                        previous_standalone_comment_line is None
                        or line_number != previous_standalone_comment_line + 1
                    ):
                        n_line_comments += 1

                    previous_standalone_comment_line = line_number

                # ------------------------------------------
                # Inline comment
                # ------------------------------------------
                else:
                    n_line_comments += 1
                    line_comment_doubles += 1  # <-- added: counts comment lines that also contain code
                    previous_standalone_comment_line = None

                    # Inline comments break a consecutive
                    # standalone-comment block
                    # previous_standalone_comment_line = None

    except (tokenize.TokenError, IndentationError):
        pass

    # --------------------------------------------------
    # 2. Find every string literal using the AST
    # --------------------------------------------------
    n_block_comments = 0
    block_comment_lines = 0
    block_comment_blank_lines = 0

    source_lines = class_code.splitlines()

    try:
        tree = ast.parse(class_code)

        for node in ast.walk(tree):

            if isinstance(node, ast.Constant) and isinstance(node.value, str):

                source = ast.get_source_segment(class_code, node)

                if source is None:
                    continue

                # Remove prefixes such as r, u, b, f, etc.
                stripped = source.lstrip()

                while stripped and stripped[0].lower() in "rubf":
                    stripped = stripped[1:]

                # Only count triple-quoted strings
                if not (
                    stripped.startswith('"""')
                    or stripped.startswith("'''")
                ):
                    continue

                start_line = node.lineno
                end_line = getattr(node, "end_lineno", node.lineno)

                n_block_comments += 1

                block_comment_lines += (
                    end_line - start_line + 1
                )

                string_lines = source_lines[
                    start_line - 1:end_line
                ]

                block_comment_blank_lines += sum(
                    1
                    for line in string_lines
                    if not line.strip()
                ) #bug, needs to count all of the blank lines all of the block comments

    except SyntaxError:
        pass

    return pd.Series({
        "n_line_comments": n_line_comments,
        "line_comment_lines": line_comment_lines,
        "n_block_comments": n_block_comments,
        "block_comment_lines": block_comment_lines,
        "block_comment_blank_lines": block_comment_blank_lines,
        "double_count_lines": line_comment_doubles
    })

###########TESTS##############

def cliffs_delta(x, y):
    x = np.asarray(x)
    y = np.asarray(y)

    greater = 0
    less = 0

    for xi in x:
        greater += np.sum(xi > y)
        less += np.sum(xi < y)

    return (greater - less) / (len(x) * len(y))



def run_metric_tests(
    df,
    group_col="source",
    group_a="SideProject",
    group_b="Vibecoding",
    exclude_cols=None,
):
    if exclude_cols is None:
        exclude_cols = {
            "url", "commit", "proj_name",
            "file_path", "file_name", "fn_name", "fn_sig",
            "fn_code", "origin_class", "called_in_files"
        }

    results = []

    # Convert booleans to 0/1
    test_df = df.copy()
    bool_cols = test_df.select_dtypes(include="bool").columns
    test_df[bool_cols] = test_df[bool_cols].astype(int)

    candidate_cols = [
        col for col in test_df.columns
        if col not in exclude_cols
        and col != group_col
        and pd.api.types.is_numeric_dtype(test_df[col])
    ]

    for col in candidate_cols:
        a = test_df.loc[test_df[group_col] == group_a, col].dropna()
        b = test_df.loc[test_df[group_col] == group_b, col].dropna()

        if len(a) == 0 or len(b) == 0:
            continue

        # Skip columns with no variation
        if a.nunique() <= 1 and b.nunique() <= 1:
            continue

        # if (col == "avg_lines_in_comment"):
        #         a = a[a!=0]
        #         b = b[b!=0]

        
        if col == "is_async":
            stat,p =  chi2_contingency(a,b)
        else:
            stat, p = mannwhitneyu(a, b, alternative="two-sided")
        delta = cliffs_delta(b,a)
        print(col)

        results.append({
            "metric": col,
            f"{group_a}_n": len(a),
            f"{group_b}_n": len(b),
            f"{group_a}_median": a.median(),
            f"{group_b}_median": b.median(),
            f"{group_a}_mean": a.mean(),
            f"{group_b}_mean": b.mean(),
            "effect_size_median_diff": b.median() - a.median(),
            "u_stat": stat,
            "effect_direction":
            "Vibecoding > SideProject"
            if delta>0
            else "SideProject > Vibecoding",
            "size": delta,
            "p_value": p,
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df["p_adj_bh"] = multipletests(
            results_df["p_value"],
            method="fdr_bh"
        )[1]

        results_df = results_df.sort_values("p_adj_bh")

    return results_df



def add_origin_class_from_raw_text(
    functions_df,
    classes_df,
    project_col="project",
    file_col="file_path",
    fn_code_col="fn_code",
    class_code_col="class_code",
    class_name_col="class_name",
):
    functions = functions_df.copy()
    classes = classes_df.copy()

    functions["origin_class"] = pd.NA

    for fn_idx, fn_row in functions.iterrows():
        fn_code = str(fn_row[fn_code_col]).strip()

        possible_classes = classes[
            (classes[project_col] == fn_row[project_col]) &
            (classes[file_col] == fn_row[file_col])
        ]

        matches = []

        for _, class_row in possible_classes.iterrows():
            class_code = str(class_row[class_code_col])

            if fn_code and fn_code in class_code:
                matches.append({
                    "class_name": class_row[class_name_col],
                    "class_size": len(class_code),
                })

        if matches:
            # If nested classes exist, choose the smallest matching class
            best_match = min(matches, key=lambda x: x["class_size"])
            functions.at[fn_idx, "origin_class"] = best_match["class_name"]

    return functions

def add_cyclomatic_complexity(
    functions_df,
    code_col="fn_code",
    out_col="cyclomatic_complexity"
):
    df = functions_df.copy()

    def compute(code):
        try:
            results = cc_visit(str(code))
            if not results:
                return None
            return results[0].complexity
        except Exception:
            return None

    df[out_col] = df[code_col].apply(compute)

    return df


def deduplicate_doubles(fn_code):
    text = re.sub(r"\n\n", "\n", fn_code)
    return text

def replace_doubled_newlines(df):
    df["fn_code"] = df["fn_code"].apply(deduplicate_doubles)
    return df

def count_function_lines(function_code):
    if not isinstance(function_code, str):
        return 0

    return len(function_code.splitlines())


if __name__ == "__main__":
    #setup
    fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])
    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'n_args', 'n_args': 'line_count','line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    fn_df.drop_duplicates(inplace=True)
    

    # of lines  # of variables, # of arguments # of functions called by function
    fn_df["var_list"] = fn_df["var_list"].apply(literal_eval)
    fn_df["n_vars"] = fn_df["var_list"].str.len()
    fn_df["fn_called"] = fn_df["fn_called"].apply(literal_eval)
    fn_df["n_called"] = fn_df["fn_called"].str.len()

    # Fixing my mistakes in the function space, need to replace 
    # the ... you know
    fn_df = replace_doubled_newlines(fn_df)
    fn_df["line_count"] = fn_df["fn_code"].apply(count_function_lines)

    fn_df["n_blank_lines"] = fn_df["fn_code"].apply(count_blank_lines)

    #avg line length
    fn_df["n_characters"] = fn_df["fn_code"].apply(count_characters)
    fn_df[[
    "n_line_comments",
    "line_comment_lines",
    "n_block_comments",
    "block_comment_lines",
    "block_comment_blank_line",
    "double_count_lines"
    ]] = fn_df["fn_code"].apply(count_comments)

    # of times function is called
    df_calls = pd.read_csv("../dataset_features/all_calls.csv", names= ["url", "commit", "project", "file_path", "file", "calls"])
    df_calls.drop_duplicates(inplace=True)
    df_calls["calls"] = df_calls["calls"].apply(literal_eval)



    df_imports = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df_imports.drop_duplicates(inplace=True)
    df_imports["imports"] = df_imports["imports"].apply(literal_eval)

    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)
    # fn_df["temp_full_text"] = fn_df["fn_sig"] + "\n" + fn_df["fn_code"]
    #double-checked, and fn_code already contains the function header

    functions_df = add_cyclomatic_complexity(fn_df, code_col="fn_code")
    print(functions_df.columns)

    functions_with_classes = add_origin_class_from_raw_text(
    functions_df,
    class_df,
    project_col="url",
    file_col="file_path",
    fn_code_col="fn_code",
    class_code_col="class_code",
    class_name_col="class_name",
    )
    functions_with_classes.to_csv("fn_origin_test.csv")
    print(functions_with_classes.columns)
    # print(functions_with_classes.head())
    # print(df_imports.head())
    long_imports = make_imports_long(df_imports)


#     classes_df = add_function_call_counts_same_file(
#     functions_df=fn_df,
#     calls_df=df_calls,
#     project_col="url",
#     function_col="fn_name",
#     calls_col="calls"
# )
    # print(fn_df.columns)
    # print(classes_df.columns)
    # print(classes_df.iloc[classes_df.n_times_called.idxmax()])
    # print("load_state check")
    # print(classes_df.iloc[(classes_df.fn_name == "load_state") ])

    # # of times a function is imported


    
    # print(long_imports.head())
    calls_df = make_matches (
    functions_with_classes,
    long_imports,
    project_col="url",
    class_col="fn_name",
    class_file_col="file_path",
    imports_col="imports",     
    is_fn=True
)
    #TO: DO add import locations
    
    classes_df = add_function_call_counts_with_imports(
        functions_df=calls_df,
        calls_df=df_calls,
        imports_df=df_imports,
        project_col="url",
        function_col="fn_name",
        calls_col="calls",
        file_col="file_path",
        imports_col="imports",
   
    )
    # print(calls_df.columns)
    # calls_df[["n_same_file_calls", "n_imported_calls"]] = calls_df[["n_same_file_calls", "n_imported_calls"]].fillna(0)
    calls_df.to_csv("temp_fn_calls_checking.csv")
    # print(calls_df.iloc[(calls_df.fn_name == "load_state") ])
    # print(df_imports.imports.iloc[(df_imports.file_path == "spec-kitty/src/specify_cli/cli/commands/merge.py") ])

    calls_df["class_module_file"] = (
    calls_df["file_path"]
    .str.replace(".py", "", regex=False)
    .str.split("/")
    .str[-1]
)

    dupes = (
        calls_df.groupby(["url", "commit",  "file_path", "fn_name"])
        .size()
        .sort_values(ascending=False)
    )
    dupes=dupes[dupes>1]
    print(f"number dupe fn names {dupes.sum}")
    dupes.to_csv("fn_duplicates.csv")

    # print(dupes[dupes > 1].head(20))
    short_class = classes_df.filter(items=["url", "file_path", "fn_name", "fn_code", "n_same_file_calls", "n_imported_calls", "called_in_files"])
    
    both = fn_df.merge(short_class, how="left", on=["url", "file_path","fn_name", "fn_code"])
    short_calls= calls_df.filter(items=["url", "file_path", "fn_name", "fn_code", "n_times_imported", "origin_class", "import_locations", "cyclomatic_complexity"])
    both_2 = both.merge(short_calls, how = "left", on=["url", "file_path","fn_name", "fn_code"])
    # print(both_2.columns)
    
    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]

    py_vc = make_mask(source, both_2, names[0])
    py_sp = make_mask(source, both_2, names[1])


    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    used_all = pd.concat([py_sp, py_vc], ignore_index=True)
    print(used_all.columns)
    used_all["block_comment_lines"] = used_all["block_comment_lines"] - used_all["block_comment_blank_line"]
    used_all["n_code_lines"] =used_all["line_count"]  - used_all["line_comment_lines"] - used_all["block_comment_lines"] + used_all["double_count_lines"] - used_all["n_blank_lines"]
    used_all["total_lines"] = used_all["line_count"] #used_all["line_count"] + used_all["line_comment_lines"] + used_all["block_comment_lines"] + used_all["n_blank_lines"] - used_all["block_comment_blank_line"] - used_all["double_count_lines"]

    # used_all["n_vars_bline"] = used_all["n_vars"]/used_all["n_code_lines"]
    # used_all["n_blank_lines_bline"] = used_all["n_blank_lines"]/used_all["n_code_lines"]
    # used_all["n_characters_tot_bline"] = used_all["n_characters"]/(used_all["n_code_lines"]+used_all["line_comment_lines"]+used_all["block_comment_lines"])
    # used_all["n_line_comments_blines"] = used_all["n_line_comments"]/used_all["n_code_lines"] #consider not using this one?
    # used_all["line_comment_lines_bline"] = used_all["line_comment_lines"]/used_all["n_code_lines"]
    # used_all["n_block_comments_bline"] = used_all["n_block_comments"]/used_all["n_code_lines"]
    # used_all["block_comment_lines_bline"] = used_all["block_comment_lines"]/used_all["n_code_lines"]
    # used_all["n_code_lines_line"] = used_all["n_code_lines"]/used_all["line_count"]
    # used_all["n_called_bline"] = used_all["n_called"]/used_all["n_code_lines"]
    # used_all["n_args_bline"] = used_all["n_args"]/used_all["n_code_lines"]
    # used_all["n_total_calls"] = used_all["n_imported_calls"] + used_all["n_same_file_calls"]

    used_all["n_comments_lines"] = used_all["line_comment_lines"] + used_all["block_comment_lines"]
    used_all["n_comments"] = used_all["n_line_comments"] + used_all["n_block_comments"]



    used_all["n_vars_by_line"] = np.divide(
        used_all["n_vars"],
        used_all["n_code_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_code_lines"] != 0,
    )

    used_all["percent_comments"] = np.divide(
        used_all["n_comments_lines"],
        used_all["total_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_code_lines"] != 0,
    ).replace([np.inf, -np.inf], np.nan)

    used_all["percent_blank"] = np.divide(
        used_all["n_blank_lines"],
        used_all["total_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["total_lines"] != 0,
    )

    used_all["percent_code"] = np.divide(
        used_all["n_code_lines"],
        used_all["total_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["total_lines"] != 0,
    )

    used_all["avg_lines_in_comment"] = np.divide(
        used_all["n_comments_lines"],
        used_all["n_comments"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_comments"] != 0,
    ).replace([np.inf, -np.inf], np.nan) #I think I actually need a drop zeros for this one and for class
    print(f"smallest average comment {used_all["avg_lines_in_comment"].min()}")



    used_all["n_characters_total_by_line"] = np.divide(
        used_all["n_characters"],
        used_all["n_code_lines"] + used_all["line_comment_lines"] + used_all["block_comment_lines"],
        out = np.full(len(used_all), np.nan),
        where=(used_all["n_code_lines"] + used_all["line_comment_lines"] + used_all["block_comment_lines"]) != 0,
    )

    # used_all["n_line_comments_by_lines"] = np.divide(
    #     used_all["n_line_comments"],
    #     used_all["n_code_lines"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_code_lines"] != 0,
    # )

    # used_all["line_comment_lines_by_line"] = np.divide(
    #     used_all["line_comment_lines"],
    #     used_all["n_code_lines"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_code_lines"] != 0,
    # )

    # used_all["avg_line_comment_len"] = np.divide(
    #     used_all["line_comment_lines"],
    #     used_all["n_line_comments"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_line_comments"] != 0,
    # )

    # used_all["n_block_comments_by_line"] = np.divide(
    #     used_all["n_block_comments"],
    #     used_all["n_code_lines"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_code_lines"] != 0,
    # )
    # used_all["block_comment_lines_by_line"] = np.divide(
    #     used_all["block_comment_lines"],
    #     used_all["n_code_lines"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_code_lines"] != 0,
    # )


    # used_all["avg_block_comment_len"] = np.divide(
    #     used_all["block_comment_lines"],
    #     used_all["n_block_comments"],
    #     out=np.zeros(len(used_all), dtype=float),
    #     where=used_all["n_block_comments"] != 0,
    # )

    used_all["n_code_lines_by_line"] = np.divide(
        used_all["n_code_lines"],
        used_all["line_count"],
        out = np.full(len(used_all), np.nan),
        where=used_all["line_count"] != 0,
    )

    used_all["n_called_by_line"] = np.divide(
        used_all["n_called"],
        used_all["n_code_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_code_lines"] != 0,
    )

    used_all["n_args_by_line"] = np.divide(
        used_all["n_args"],
        used_all["n_code_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_code_lines"] != 0,
    )

    used_all["n_total_calls"] = (
        used_all["n_imported_calls"] + used_all["n_same_file_calls"]
    )
    # used_all["middleman"] = (
    #     used_all["n_imported_calls"] + used_all["n_same_file_calls"]
    # )

    df_all_py_files = pd.read_csv("proj_level_py.csv")
    print(df_all_py_files.columns)

    df_py_files = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    df_py_files = df_py_files[df_py_files["extn"] == "py"]
    df_all_py_files["n_code_lines"] = df_all_py_files["n_lines"] - df_all_py_files["n_blank_lines"] #- df_py_files["blank_lines"] - df_py_files["n_comment_lines_block"] - df_py_files["n_comment_lines_line"]
    df_py_files["n_code_lines"] = df_py_files["n_lines"] = df_py_files["blank_lines"]

    colnames=["url","commit","proj_name","file_path","file_name","new_url","comments", "type", "raw"] 
    comments = pd.read_csv("../dataset_features/comments.csv", names=colnames, header=None)
    comments.drop_duplicates(inplace=True)

    comments[["comment_kind", "comment_n_lines"]] = (
    comments.apply(comment_stats, axis=1)
    )

    comment_summary = (
    comments.groupby(["file_path"])
      .agg(
          n_comments=("raw", "size"),
          n_comment_lines=("comment_n_lines", "sum")
      )
      .reset_index()
    )

    # comment_summary = comment_summary.pivot_table(
    # index="file_path",
    # columns="comment_kind",
    # values=["n_comments", "n_comment_lines"],
    # fill_value=0
    # )
    # print(comm)

    #subtract n_comments 



    used_all["n_lines_in_proj"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_files"]
    )


    used_all["n_files"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_files"]
    )

    used_all["n_files"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_files"]
    ) 
    used_all["n_proj_lines"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_code_lines"]
    ) #add another thing here to get the number of blank lines per project

    used_all["n_file_lines"] = used_all["file_path"].map(
    df_py_files.set_index("file_path")["n_code_lines"]
    )

    used_all["n_comment_lines"] = used_all["file_path"].map(
    comment_summary.set_index("file_path")["n_comment_lines"]
    )

    used_all["code_lines_in_file"] = used_all["n_file_lines"] - used_all["n_comment_lines"]

    used_all["n_times_imported_by_file"] = np.divide(
        used_all["n_times_imported"],
        used_all["n_files"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_files"] != 0,
    )

    used_all["n_total_calls_by_total"] = np.divide(
        used_all["n_times_imported"],
        used_all["n_proj_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_proj_lines"] != 0,
    )

    used_all["n_times_called_outside_by_total"] = np.divide(
        used_all["n_imported_calls"],
        used_all["n_proj_lines"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_proj_lines"] != 0,
    )

    used_all["n_times_called_inside_by_file"] = np.divide(
        used_all["n_same_file_calls"],
        used_all["code_lines_in_file"],
        out = np.full(len(used_all), np.nan),
        where=used_all["code_lines_in_file"] != 0,
    )

    used_all.drop(columns=['n_proj_lines', "n_files", "code_lines_in_file", "n_proj_lines", "n_file_lines", "n_comment_lines"], inplace=True)

    




    



    used_all.to_csv("fn_level_metrics.csv")

    # print(used_all.iloc[1])
    # print(used_all.columns)
    stats_results = run_metric_tests(
    used_all,
    group_col="source",
    group_a="SideProject",
    group_b="Vibecoding"
)
    stats_results= stats_results.sort_values("p_adj_bh")

    stats_results.to_csv("fn_level_py.csv")


   



    # 

    # print(f"{len(calls_df)-len(calls_df.fn_name.unique())}")
    # print(calls_df.shape)
    # print(calls_df.iloc[calls_df.n_times_imported.idxmin()])
    # print(calls_df.iloc[(calls_df.file_path == "steward-protocol/vibe_core/specialists/base_specialist.py") & (calls_df.url == "https://github.com/kimeisele/steward-protocol ") ])
    # assert (calls_df.loc[calls_df.file_path == "steward-protocol/vibe_core/specialists/base_specialist.py"])

 
    # for file 
    # print(module_matches_file("hooks.shared_state", "shared_state", "some.package.hooks.shared_state"))




