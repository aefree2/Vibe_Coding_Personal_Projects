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

from mixed_effects_fn import make_imports_long, extract_call_names, add_origin_class_from_raw_text, count_comments, deduplicate_doubles
#count_line_comments 



def replace_doubled_newlines(df):
    df["class_code"] = df["class_code"].apply(deduplicate_doubles)
    return df

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



import ast
import pandas as pd
from pathlib import Path


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

# def extract_call_names(calls):
#     if calls is None:
#         return []

#     if isinstance(calls, str):
#         try:
#             calls = ast.literal_eval(calls)
#         except Exception:
#             calls = [calls]

#     if not isinstance(calls, (list, set, tuple)):
#         return []

#     names = []

#     for call in calls:
#         call = str(call).strip()
#         match = re.match(r"^([A-Za-z_][\w\.]*)\s*\(", call)

#         if match:
#             names.append(match.group(1))

#     return names



def extract_function_names(fn_list):
    pattern = re.compile(r"def\s+([A-Za-z_]\w*)\s*\(")
    return [
        m.group(1)
        for fn in fn_list
        if (m := pattern.search(fn))
    ]

def add_function_call_counts_with_imports(
    functions_df,
    calls_df,
    imports_df,
    project_col="url",
    function_col="class_name",
    calls_col="calls",
    file_col="file_path",
    imports_col="imports",
):
    #I think I am just going to get the insantiations
    print("Functions df")
    print(functions_df)
    
    # functions_df.origin_class.fillna("NaN", inplace=True)
    functions = functions_df.copy()
    calls = calls_df.copy()
    imports = imports_df.copy()
    # print(f" function columns: {functions.columns}")

    functions["function_module"] = functions[file_col].apply(module_from_file_path)
    functions["function_module_file"] = functions["function_module"].apply(module_file_name)
    # print(functions.shape)
    # functions["fn_count"] = functions["fn_count"].apply(literal_eval)

    functions["function_names"] = functions["fn_count"].apply(extract_function_names)
    # print("functions")
    # print(functions.fn_count)
    # print("function names")
    # print(functions.function_names)
    # functions["function_names"] = functions["function_names"].apply(
    # lambda x: x + [np.nan] if isinstance(x, list) else [np.nan]
    # )
    # functions = functions.explode("function_names")
    # print(functions.class_name)
    # print("functions")
    # functions.to_csv("class_function_name_check.csv") #seems to be fine
    # print(functions.function_names)

    

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
    print("calls long")
    print(calls_long.head())

    result = functions.copy()

    if calls_long.empty:
        result["n_times_called"] = 0
        return result

    # -------------------------
    # 2. Same-file matches
    # -------------------------
    print("functions")
    print(functions)

    same_file_matches = calls_long.merge(
        functions,
        left_on=[project_col, file_col, "call_name",],
        right_on=[project_col, file_col,function_col,],
        how="inner",
    ) # assuming that there is only one function with the same name per file (see graph for why that is not true)
    

    same_file_matches["match_type"] = "same_file"

    same_file_matches["called_in_file"] = same_file_matches[file_col]
    same_file_matches.to_csv("test_same_file_class_call.csv")
    print("same file matches")
    print(same_file_matches.shape)

    

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
    print(imports_long.columns)
    print(calls_long.columns)

    other_file_matches = calls_long.merge(
        imports_long,
        left_on=[project_col, file_col, "call_name"],
        right_on=[project_col, "import_locations", function_col],
        how="inner",
        suffixes=("_fn", "_call"),
    ) #fixed the problem on the other side, so it will not catch self.__whatever___
    # all_matches = same_file_matches
    # print("other files")
    other_file_matches["match_type"] = "on_import"

    # print(other_file_matches.head())
    other_file_matches.rename(columns={"file_path_call": file_col}, inplace=True)
    print("other file matches")
    print(other_file_matches)
    other_file_matches["called_in_file"] = other_file_matches[f"{file_col}_fn"]
    all_matches = pd.concat([same_file_matches, other_file_matches])
    # print(all_matches.shape)
    # all_matches.rename(columns={"file_path_fn": file_col}, inplace=True)

    all_matches.to_csv("test_same_file_call.csv")
    # print(all_matches[all_matches.match_type == ])
    # print(all_matches.match_type.value_counts())
    print("all_matches")
    print(all_matches)
    


    # -------------------------
    # 6. Count matched calls
    # -------------------------
    counts = (
        all_matches.groupby([project_col, file_col, function_col]).size()
        .reset_index(name="n_times_called")
    )

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
    print("counts")
    print(counts)
    # print(counts.shape)

    result = functions.merge(
        counts,
        on=[project_col, file_col, function_col],
        how="left",
    )
    print("results")
    print(result)

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
    result["n_times_invoked"] = result["n_imported_calls"] + result["n_same_file_calls"]
    #we are going to get overcounting when a function matches a class of the same name in the same file

    return result




def add_class_invocation_counts_with_imports(
    classes_df,
    calls_df,
    imports_df,
    project_col="project",
    class_col="class_name",
    calls_col="calls",
    file_col="file_path",
    imports_col="imports",
):
    classes = classes_df.copy()
    calls = calls_df.copy()
    imports = imports_df.copy()

    classes["class_module"] = classes[file_col].apply(module_from_file_path)
    classes["class_module_file"] = classes["class_module"].apply(module_file_name)

    # -------------------------
    # 1. Make calls long
    # -------------------------
    call_rows = []

    for _, row in calls.iterrows():
        for call_name in extract_call_names(row[calls_col]):
            call_rows.append({
                project_col: row[project_col],
                file_col: row[file_col],
                "call_name": call_name,
            })

    calls_long = pd.DataFrame(call_rows)

    result = classes.copy()

    if calls_long.empty:
        result["n_times_invoked"] = 0
        return result

    # -------------------------
    # 2. Same-file class matches
    # -------------------------
    same_file_matches = calls_long.merge(
        classes,
        left_on=[project_col, file_col, "call_name"],
        right_on=[project_col, file_col, class_col],
        how="inner",
    )

    same_file_matches["match_type"] = "same_file"

    # -------------------------
    # 3. Build imports_long
    # -------------------------
    import_rows = []

    for _, row in imports.iterrows():
        parsed_imports = parse_imports_cell(row[imports_col])

        for imp in parsed_imports:
            import_rows.append({
                project_col: row[project_col],
                file_col: row[file_col],
                "import_module": imp["import_module"],
                "import_module_file": module_file_name(imp["import_module"]),
                "import_name": imp["import_name"],
                "import_type": imp["import_type"],
            })

    imports_long = pd.DataFrame(import_rows)

    if imports_long.empty:
        all_matches = same_file_matches
    else:
        # -------------------------
        # 4. from module import ClassName
        # -------------------------
        from_imports = imports_long[
            imports_long["import_type"].eq("from")
        ].copy()

        from_import_matches = (
            calls_long
            .merge(
                from_imports,
                left_on=[project_col, file_col, "call_name"],
                right_on=[project_col, file_col, "import_name"],
                how="inner",
            )
            .merge(
                classes,
                left_on=[project_col, "import_module_file", "call_name"],
                right_on=[project_col, "class_module_file", class_col],
                how="inner",
                suffixes=("_caller", ""),
            )
        )

        from_import_matches["match_type"] = "from_import"

        # -------------------------
        # 5. import module + module.ClassName()
        # -------------------------
        module_imports = imports_long[
            imports_long["import_type"].eq("module")
        ].copy()

        qualified_calls = calls_long.copy()

        split = qualified_calls["call_name"].str.rsplit(".", n=1, expand=True)

        qualified_calls["call_qualifier"] = split[0]
        qualified_calls["call_class"] = split[1]

        qualified_calls = qualified_calls[
            qualified_calls["call_class"].notna()
        ].copy()

        module_import_matches = (
            qualified_calls
            .merge(
                module_imports,
                left_on=[project_col, file_col, "call_qualifier"],
                right_on=[project_col, file_col, "import_module_file"],
                how="inner",
            )
            .merge(
                classes,
                left_on=[project_col, "import_module_file", "call_class"],
                right_on=[project_col, "class_module_file", class_col],
                how="inner",
                suffixes=("_caller", ""),
            )
        )

        module_import_matches["match_type"] = "module_import"

        all_matches = pd.concat(
            [
                same_file_matches,
                from_import_matches,
                module_import_matches,
            ],
            ignore_index=True,
        )

    # -------------------------
    # 6. Count matched class invocations
    # -------------------------
    counts = (
        all_matches
        .groupby([project_col, file_col, class_col])
        .size()
        .reset_index(name="n_times_invoked")
    )

    result = result.merge(
        counts,
        on=[project_col, file_col, class_col],
        how="left",
    )

    result["n_times_invoked"] = (
        result["n_times_invoked"]
        .fillna(0)
        .astype(int)
    )

    return result

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

# def make_imports_long(imports_df, project_col="url", imports_col="imports"):
#     rows = []

#     for _, row in imports_df.iterrows():
#         project = row[project_col]
#         imports = normalize_imports(row[imports_col])

#         for imp in imports:
#             rows.append({
#                 project_col: project,
#                 "import_module": imp["import_module"],
#                 "import_symbol": imp["import_symbol"]
#             })

#     return pd.DataFrame(rows)


def make_module_suffixes(module_path):
    """
    Example:
    repo.vibe_core.mahamantra.kernel.phoenix

    returns:
    [
      "repo.vibe_core.mahamantra.kernel.phoenix",
      "vibe_core.mahamantra.kernel.phoenix",
      "mahamantra.kernel.phoenix",
      "kernel.phoenix",
      "phoenix"
    ]
    """
    parts = str(module_path).split(".")
    return [".".join(parts[i:]) for i in range(len(parts))]


def add_module_suffix_rows(classes, module_path_col="class_module_path"):
    rows = []

    for idx, row in classes.iterrows():
        for suffix in make_module_suffixes(row[module_path_col]):
            new_row = row.to_dict()
            new_row["module_match_key"] = suffix
            rows.append(new_row)

    return pd.DataFrame(rows)

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
    # print("classes")
    # print(classes.head())
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
    # print("symbol candidates")
    # print(symbol_candidates.head())

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
    # print("symbol_matches")
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
    # print("module_matches")
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
    # print(f"all_matches: {all_matches.head()}")
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
    # print("result")
    # print(result.head())
    return result


def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    mask = (df_files["url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files


def normalize_code(code):
    if not isinstance(code, str):
        return ""

    # If code contains literal "\n", convert them to real newlines
    if "\\n" in code and "\n" not in code:
        code = code.encode("utf-8").decode("unicode_escape")

    return code


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
            "file_path", "file_name", "class_name", "class_sig",
            "class_code", "parents_classes_x"
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
        #     a = a[a!=0]
        #     b = b[b!=0]
        if col == "is_child_class":
            print (a.value_counts())
            print(b.value_counts())
            table = np.array([
                [a.sum(), len(a) - a.sum()],
                [b.sum(), len(b) - b.sum()]
            ])

            chi2, p, dof, expected = chi2_contingency(table)
        else:
            stat, p = mannwhitneyu(a, b, alternative="two-sided", nan_policy='raise')
        
        if p == 0:
            print(col)
            print(repr(p))
            print(f"{p:.30e}")

            print(len(a), len(b))
            print(a.dtype, b.dtype)
            print(np.isfinite(a).all(), np.isfinite(b).all())
            print(np.isnan(a).sum(), np.isnan(b).sum())

            print(np.min(a), np.max(a))
            print(np.min(b), np.max(b))

            print(np.unique(a)[:10])
            print(np.unique(b)[:10])
        delta = cliffs_delta(b,a)

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
    print(results_df.isna().sum())

    if not results_df.empty:
        print("not empty")
        results_df["p_adj_bh"] = multipletests(
            results_df["p_value"],
            method="fdr_bh"
        )[1]
        print(results_df.p_adj_bh)

        results_df = results_df.sort_values("p_adj_bh")

    return results_df


def count_instance_variables(class_code):
    try:
        tree = ast.parse(class_code)
    except SyntaxError:
        return None

    instance_vars = set()

    for node in ast.walk(tree):
        # self.x = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    instance_vars.add(target.attr)

        # self.x += ...
        elif isinstance(node, ast.AugAssign):
            target = node.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                instance_vars.add(target.attr)

        # self.x: int = ...
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                instance_vars.add(target.attr)

    return len(instance_vars)

def count_blank_lines(function_code):
    if not isinstance(function_code, str):
        return 0

    return sum(
        1 for line in function_code.splitlines()
        if not line.strip()
    )


def class_call_and_inheritance_metrics(class_code):
    if not isinstance(class_code, str):
        return pd.Series({
            "n_function_calls": 0,
            "is_child_class": False,
            "parent_classes": []
        })

    try:
        tree = ast.parse(class_code)
    except SyntaxError:
        return pd.Series({
            "n_function_calls": 0,
            "is_child_class": False,
            "parent_classes": []
        })

    class_node = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)),
        None
    )

    if class_node is None:
        return pd.Series({
            "n_function_calls": 0,
            "is_child_class": False,
            "parent_classes": []
        })

    n_function_calls = sum(
        isinstance(node, ast.Call)
        for node in ast.walk(class_node)
    )

    parent_classes = []

    for base in class_node.bases:
        if isinstance(base, ast.Name):
            parent_classes.append(base.id)

        elif isinstance(base, ast.Attribute):
            parent_classes.append(ast.unparse(base))

        elif isinstance(base, ast.Subscript):
            parent_classes.append(ast.unparse(base))

        else:
            parent_classes.append(ast.unparse(base))

    return pd.Series({
        "n_function_calls": n_function_calls,
        "is_child_class": len(parent_classes) > 0,
        "parent_classes": parent_classes
    })

def add_child_counts(df):
    # Count references to each parent class within each project
    child_counts = (
        df.explode("parent_classes")
          .dropna(subset=["parent_classes"])
          .groupby(["url", "parent_classes"])
          .size()
          .rename("n_child_classes")
          .reset_index()
    )

    # Match counts back onto classes
    result = df.merge(
        child_counts,
        left_on=["url", "class_name"],
        right_on=["url", "parent_classes"],
        how="left"
    )

    result["n_child_classes"] = (
        result["n_child_classes"]
        .fillna(0)
        .astype(int)
    )

    return result.drop(columns=["parent_classes_y"], errors="ignore")

def div_by_zero(df, num_col, div_col):
    return np.divide(
        df[num_col],
        df[div_col],
        out = np.full(len(used_all), np.nan),
        where=df[div_col] != 0,
    )
 
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



if __name__ == "__main__":
    #setup
    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)
    # fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])
    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'n_args', 'n_args': 'line_count','line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    class_df.drop_duplicates(inplace=True)
    class_df = replace_doubled_newlines(class_df)

    class_df["fn_count"] = class_df["fn_count"].apply(literal_eval)
    class_df["n_functions"] = class_df["fn_count"].str.len()

    #n_instance_vars
    class_df["n_instance_vars"] = class_df["class_code"].apply(count_instance_variables)


    # class_df["n_blank_lines"] = class_df["class_code"].apply(count_blank_lines)

    #avg line length
    class_df["n_characters"] = class_df["class_code"].apply(count_characters)

    # lines of comments,  # line comments, # block comments
    class_df[[
    "n_line_comments",
    "line_comment_lines",
    "n_block_comments",
    "block_comment_lines",
    "block_comment_blank_line",
    "double_count_lines"
    ]] = class_df["class_code"].apply(count_comments)

    # # of lines of code,  # lines blank
    

    class_df["n_blank_lines"] = class_df["class_code"].apply(count_blank_lines)
    # class_df["total_lines"] = class_df["line_count"] + class_df["line_comment_lines"] + class_df["block_comment_lines"] + class_df["n_blank_lines"]
    # inheritance, # of functions called,
    class_df[[
    "n_function_calls",
    "is_child_class",
    "parent_classes"
    ]] = class_df["class_code"].apply(class_call_and_inheritance_metrics)

    #direct child inheritence
    df = add_child_counts(class_df)
    print(class_df.columns)
    print(df.columns)
    print(df.iloc[df.n_child_classes.idxmax()])
    
    # fn_df


    # of times function is called IDK about this one bro
    df_calls = pd.read_csv("../dataset_features/all_calls.csv", names= ["url", "commit", "project", "file_path", "file", "calls"])
    df_calls.drop_duplicates(inplace=True)
    df_calls["calls"] = df_calls["calls"].apply(literal_eval)

    df_imports = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df_imports.drop_duplicates(inplace=True)
    df_imports["imports"] = df_imports["imports"].apply(literal_eval)


    print("counts_columns")
 
    # # of times a class is imported

    # print(df_imports.head())
    long_imports = make_imports_long(df_imports)

    
    # print(long_imports.head())
    calls_df = make_matches (
    df,
    long_imports,
    project_col="url",
    class_col="class_name",
    class_file_col="file_path",
    imports_col="imports",
    is_fn=False
)
    
    classes_with_counts = add_function_call_counts_with_imports(
    functions_df=calls_df,
    calls_df=df_calls,
    imports_df=df_imports,
    project_col="url",
    function_col="class_name",
    calls_col="calls",
    file_col="file_path",
    imports_col="imports",
    )

    # classes_with_counts["n_times_invoked", "n_imported_calls", "n_same_file_calls"] =  classes_with_counts["n_times_invoked", "n_imported_calls", "n_same_file_calls"].fillna(0)

    print(classes_with_counts.columns)
#     print(classes_df.columns)
#     print(classes_df.iloc[classes_df.n_times_called.idxmax()])
    print("load_state check")
    print(classes_with_counts.iloc[(classes_with_counts.class_name == "ValidationResult") ])

    # print(calls_df.columns)
    calls_df.to_csv("temp_class_calls_checking.csv")
    print(calls_df.iloc[(calls_df.class_name == "ValidationResult") ])
    # top_classes = (
    #     class_df["class_name"]
    #     .value_counts()
    #     .reset_index()
    # )

    # top_classes.columns = ["class_name", "count"]

    # print(top_classes.head(20))

    

    # print(df_imports.imports.iloc[(df_imports.file_path == "spec-kitty/src/specify_cli/cli/commands/merge.py") ])

#     calls_df["class_module_file"] = (
#     calls_df["file_path"]
#     .str.replace(".py", "", regex=False)
#     .str.split("/")
#     .str[-1]
# )

#     dupes = (
#         calls_df.groupby(["url", "commit",  "class_module_file", "fn_name"])
#         .size()
#         .sort_values(ascending=False)
#     )

    # print(dupes[dupes > 1].head(20))
    short_class = classes_with_counts.filter(items=["url", "file_path", "class_name", "class_code", "n_times_invoked", "n_imported_calls", "n_same_file_calls", "called_in_files"])
    both = df.merge(short_class, how="left", on=["url", "file_path","class_name" , "class_code"])
    short_calls= calls_df.filter(items=["url", "file_path", "class_name", "class_code","n_times_imported", "import_locations"])
    both_2 = both.merge(short_calls, how = "left", on=["url", "file_path","class_name", "class_code"])
    # print(both_2.columns)

    both_2["n_times_imported"] =  both_2["n_times_imported"].fillna(0)

    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]

    py_vc = make_mask(source, both_2, names[0])
    py_sp = make_mask(source, both_2, names[1])


    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    used_all = pd.concat([py_sp, py_vc], ignore_index=True)
    
  
    # print(used_all.iloc[1])
    # print(used_all.columns)
    # used_all["avg_len_line_comment"] = div_by_zero(used_all, "line_comment_lines", "n_line_comments")
    # used_all["avg_len_block_comment"] = div_by_zero(used_all, "block_comment_lines", "n_block_comments")


    # used_all["n_blank_lines"] = used_all["n_blank_lines"]/2
    # used_all["line_count"] = used_all["line_count"] - used_all["n_blank_lines"]
    used_all["n_comments_lines"] = used_all["line_comment_lines"] + used_all["block_comment_lines"]
    used_all["n_comments"] = used_all["n_line_comments"] + used_all["n_block_comments"]
    # used_all["block_comment_blank_line"] = used_all["block_comment_blank_line"]/2

    used_all["n_code_lines"] =used_all["line_count"] - used_all["n_comments_lines"] - used_all["n_blank_lines"] + used_all["block_comment_blank_line"] + used_all["double_count_lines"]

    # used_all.fillna({"n_comments":0},inplace=True)
    # used_all.fillna({"n_comments_lines":0},inplace=True)

    used_all["avg_lines_in_comment"] = np.divide(
        used_all["n_comments_lines"],
        used_all["n_comments"],
        out = np.full(len(used_all), np.nan),
        where=used_all["n_comments"] != 0,
    ).replace([np.inf, -np.inf], np.nan)
    print(f"smallest average comment {used_all["avg_lines_in_comment"].min()}")
    # out=np.nan(len(used_all), dtype=float),

    used_all["percent_comments"] = div_by_zero(used_all, "n_comments_lines", "line_count")
    used_all["percent_code"] =  div_by_zero(used_all, "n_code_lines", "line_count")
    used_all["percent_blank"] = div_by_zero(used_all, "n_blank_lines", "line_count")

    used_all["n_fns_raw"] = used_all["n_functions"]
    used_all["n_instance_vars_raw"] = used_all["n_instance_vars"]


    exclude = ["url", "commit", "n_code_lines", "source", "proj_name", "file_path", "file_name", 
               "class_name", "class_sig", "parent_classes_x", "is_child_class", "class_code", "fn_count",
               "n_times_invoked", "n_same_file_calls", "n_child_classes", "n_times_imported", "n_imported_calls",
               "n_code_lines", "avg_lines_in_comment", "import_locations", "called_in_files","n_comments_lines", "total_lines", "percent_code", "percent_blank", "line_count", "n_blank_lines",
               "block_comment_blank_line", "n_fns_raw"] # "avg_len_line_comment" "avg_len_block_comment" "n_function_calls" "n_characters"
    cols = used_all.columns.difference(exclude)
    # used_all.fillna(0, inplace=True)
    #should I be dividing characters by number of code lines or by the number of non-blank lines? 





    used_all[cols] = (
        used_all[cols]
        .div(used_all["n_code_lines"], axis=0)
        .replace([np.inf, -np.inf], np.nan)
   
    )






    #THE PART WHERE I START DOING WEIRD THINGS DO NOT CHANGE THINGS HERE
    df_all_py_files = pd.read_csv("proj_level_py.csv")
    print(df_all_py_files.columns)
    df_all_py_files["n_code_lines"] = df_all_py_files["n_lines"] - df_all_py_files["n_comment_lines_block"] - df_all_py_files["n_comment_lines_line"] - df_all_py_files["n_blank_lines"]

    df_py_files = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    df_py_files = df_py_files[df_py_files["extn"] == "py"]
    df_py_files["n_code_lines"] = df_py_files["n_lines"] - df_py_files["blank_lines"] 



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

    used_all["n_files"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_files"]
    )

    used_all["n_proj_lines"] = used_all["url"].map(
    df_all_py_files.set_index("url")["n_code_lines"]
    ) 



    used_all["n_file_lines"] = used_all["file_path"].map(
    df_py_files.set_index("file_path")["n_code_lines"]
    )

    used_all["n_comment_lines"] = used_all["file_path"].map(
    comment_summary.set_index("file_path")["n_comment_lines"]
    )

    # I have already subtracted out the number of blank lines in a file, I don't need to do that again, lol
    used_all["code_lines_in_file"] = used_all["n_file_lines"] - used_all["n_comment_lines"] # - used_all["n_file_blank"] 
    # double-check that I didn't already save this for files,
    # and that I am dividng by the right number here, 
    print(used_all["n_files"])

    used_all["n_times_invoked_by_all_lines"] = div_by_zero(used_all, "n_times_invoked", "n_proj_lines")
    used_all["n_same_file_calls_by_file_size"] = div_by_zero(used_all, "n_same_file_calls", "code_lines_in_file")
    used_all["n_times_imported_by_files"] = div_by_zero(used_all, "n_times_imported", "n_files")
    used_all["n_imported_calls_by_all_lines"] = div_by_zero(used_all, "n_imported_calls", "n_proj_lines")

    func_stats = (used_all.groupby("url").agg(class_count=("url", "size"))).reset_index()

    used_all["n_classes"] = used_all["url"].map(
    func_stats.set_index("url")["class_count"]
    )

    used_all["n_child_classes_by_total_classes"] = div_by_zero(used_all, "n_child_classes", "n_classes")

    used_all.drop(columns=['n_classes', 'n_proj_lines', "n_files", "code_lines_in_file", "n_proj_lines", "n_file_lines", "n_comment_lines"], inplace=True)



    used_all.to_csv("class_level_metrics.csv")
    






    stats_results = run_metric_tests(
    used_all,
    group_col="source",
    group_a="SideProject",
    group_b="Vibecoding"
    )
    stats_results= stats_results.sort_values("p_adj_bh") 

    stats_results.to_csv("class_level_py.csv")


   



    # 

    # print(f"{len(calls_df)-len(calls_df.fn_name.unique())}")
    # print(calls_df.shape)
    # print(calls_df.iloc[calls_df.n_times_imported.idxmin()])
    # print(calls_df.iloc[(calls_df.file_path == "steward-protocol/vibe_core/specialists/base_specialist.py") & (calls_df.url == "https://github.com/kimeisele/steward-protocol ") ])
    # assert (calls_df.loc[calls_df.file_path == "steward-protocol/vibe_core/specialists/base_specialist.py"])

 
    # for file 
    # print(module_matches_file("hooks.shared_state", "shared_state", "some.package.hooks.shared_state"))




