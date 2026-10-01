from zipfile import ZipFile
import os
import glob
import shutil
import ast
import pandas as pd
import re
import csv

def make_ast(pathname):
    #make an ast from a given file
    with open(pathname, 'r') as file:
        code = file.read()
    tree = ast.parse(code)
    return tree

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
        df = pd.DataFrame(columns = ["url", "commit", "proj_name", "file_path", "file_name", "import_list"], dtype=object)
    return df


def get_imported_packages(tree):
    #does not capture from x import y
    """
    Return a set of top-level imported package names from Python source code.
    """
    #tree = ast.parse(code_str)
    
    imports = set()

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imports.add(alias.name) #.split('.')[0]
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            if node.module is not None:
                imports.add(f'{node.module}: {[alias.name for alias in node.names]}') #.split('.')[0] #shore up this for from x import y
            self.generic_visit(node)

    ImportVisitor().visit(tree)
    return imports

def find_requirements(url, commit, short_name, file_path, path="../dataset_features/requirements.csv"):
    print("Getting Requirements")
    df = load_from_checkpoint(path)
    file_name = re.split(r"/", file_path)[-1]


    with open(file_path, "r") as f:
        lines = f.readlines()
    #append_if_not_exists(df, [url, commit, short_name, file_path, file_name, lines])
    append_raw_csv(path, [url, commit, short_name, file_path, file_name, lines])
    df.to_csv(path)
    return df
    

def find_imports(url, commit, short_name, file_path, path="../dataset_features/imports.csv"):
    print("Getting Imports")
    failed_num = 0
    # df = load_from_checkpoint(path)

 
    #print(file)

    #df_classes.loc[len(df_classes)] = [proj_name, file, , ]
    #file_status = [proj_name, file, None,]
    file_name = re.split(r"/", file_path)[-1]
        
    try:
        tree = make_ast(file_path)
    except Exception as e:
        # df_failures = pd.read_csv("../dataset_features/clone_failures.csv", index_col=0)
        #append_if_not_exists(df_failures, [url, file_name, file_path, f"imports failed: {e}"])
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"imports failed: {e}"])
        return
    imports = get_imported_packages(tree) #functions contains the total code for each function
    #not_exists(df, [url, commit, short_name, file_path, file_name, imports])
    append_raw_csv(path, [url, commit, short_name, file_path, file_name, imports])
    #print(imports)
        
    # except Exception as e:
    #         failed_num = failed_num + 1
    #         print("failed in functions with: ")
    #         print(e)
    #         file_status[2] = str(e)
    #         print(file_status)
    #         df_failures.loc[len(df_failures)] = file_status
    # df.to_csv(path)
    # return df




