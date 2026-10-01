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
        file = row["file_path"]
        imports = normalize_imports(row[imports_col])

        for imp in imports:
            rows.append({
                project_col: project,
                "file_path": file,
                "import_module": imp["import_module"],
                "import_symbol": imp["import_symbol"]
            })

    return pd.DataFrame(rows)

def find_uses(imports, calls):

    return

def parse_calls(x):
    if isinstance(x, list):
        return x

    if pd.isna(x):
        return []

    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except Exception:
            return [x]

    return list(x)



if __name__ == "__main__":
    df_imports = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df_imports.drop_duplicates(inplace=True)

    df_calls = pd.read_csv("../dataset_features/all_calls.csv", names= ["url", "commit", "project", "file_path", "file", "calls"])
    df_calls.drop_duplicates(inplace=True)
    
    df_calls["calls"] = df_calls["calls"].apply(literal_eval)
    print(df_calls.head())

    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    source.drop_duplicates(inplace=True)
    names = ["Vibecoding", "SideProject"]






    df_imports["imports"] = df_imports["imports"].apply(literal_eval)
    imports_expanded = make_imports_long(df_imports)

    both = imports_expanded.merge(df_calls, on=["url", "file_path",])
    print(type(both.iloc[0]["calls"]))
    both["calls_parsed"] = both["calls"].apply(parse_calls)
    
    

    both["is_used"] = both.apply(
        lambda row: any(
            (
                s == row["import_module"]
                or f"{row['import_module']}." in s
                or (
                    pd.notna(row["import_symbol"])
                    and row["import_symbol"]
                    and (
                        s == row["import_symbol"]
                        or f"{row['import_symbol']}." in s
                    )
                )
            )
            for s in row["calls_parsed"]
        ),
        axis=1
    )
    print(both.is_used.value_counts())
    both.to_csv("both_test.csv")


    
    print(imports_expanded.head())

    # py_vc = make_mask(source, used_imports, names[0])
    # py_sp = make_mask(source, used_imports, names[1])


    # py_sp["source"] = "SideProject"
    # py_vc["source"] = "Vibecoding"

    # used_all = pd.concat([py_sp, py_vc], ignore_index=True)
    # print(used_all.is_used.value_counts())