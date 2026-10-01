import ast
import pandas as pd
import re
import csv


#Consider making this the top level tree parser

def load_from_checkpoint(path):
    #consider if there is a better way to do this...
    try:
        df = pd.read_csv(path, index_col=0)
    except:
        print("error reading in file")
        df = pd.DataFrame(columns = ["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_async"], dtype=object)
        df.to_csv(path)
    return df

def load_from_checkpoint_classes(path):
    try:
        df = pd
    except:
        print("error reading in file")
        df = pd.DataFrame(columns = ["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"], dtype=object)
        df.to_csv(path)

def load_from_checkpoint_calls(path):
    try:
        df = pd
    except:
        print("error reading in file")
        df = pd.DataFrame(columns = ["url", "commit", "proj_name", "file_path", "file_name", "call_list"], dtype=object)
        df.to_csv(path)


def append_raw_csv(location, row):
    with open(location,'a') as fd:
        writer = csv.writer(fd)
        writer.writerow(row)


def make_ast(pathname):
    #make an ast from a given file
    with open(pathname, 'r') as file:
        code = file.read()
    tree = ast.parse(code)
    return tree

def extract_fn_name_header(code, code_ast):
    classes = []
    functions = []
    n_args = []
    name_list = []
    arg_list = []
    for node in ast.walk(code_ast):
        

        #get all instances of a function being instantiated 
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            #need to just get function call line
            start = node.lineno
            end = node.end_lineno
            class_code = "".join(code[start - 2:end])

            classes.append(class_code)
            name_list.append(node.name)


            #get args
            n_args.append(len(node.args.args))
            functions.append(node)
            arg_list.append(ast.unparse(node.args))

        #primitive count (?)

    return classes, functions, n_args, name_list, arg_list

def extract_calls_varnames(code_ast,variable_names):
    #variable_names = []
    fn_calls = []
    for node in ast.walk(code_ast):
        if isinstance(node, ast.Call):
            #having some slight problems with call...
            fn_calls.append(ast.unparse(node)) 
            #begin the stupidity, or, I can 
            #
            
            
        # #Instance Variables Count
        elif isinstance(node,ast.Assign):
            name = ast.unparse(node.targets)
            #print(ast.unparse(node.targets))
            if name not in variable_names:
                variable_names.append(name)
            
    return variable_names, fn_calls

def extract_classes(code, code_ast):
    classes = []
    node_classes = []
    class_name = []
    n_functions = {}
    for node in ast.walk(code_ast):
        if isinstance(node, ast.ClassDef):
            #having some slight problems with call...
            #print(ast.dump(node,indent=4))
            #print(ast.unparse(node))
            start = node.lineno
            end = node.end_lineno
            class_code = "".join(code[start - 2:end])

            classes.append(class_code)
            class_name.append(node.name)
            node_classes.append(node)

 
    for class_ in node_classes:
        # print("Class name: ", class_.name)
        n_functions[class_.name] = []
        for node in ast.walk(class_):
            if isinstance(node, ast.FunctionDef):
                func_defs = [line.strip() for line in ast.unparse(node).splitlines() if re.match(r'^\s*def\s+\w+\s*\(.*?\)\s*:', line)]
                for fun in func_defs:
                    if class_.name in n_functions.keys():
                        n_functions[class_.name].append(fun)
                    else:
                        n_functions[class_.name] = [fun]
    #print(n_functions)
    return classes, n_functions, node_classes

# def fn_parser(python_files_list, failed_file_num, df):
#     #add another parser for class parser 
#     for file in python_files_list:
    
#         with open(file, "r") as f:
#             lines = f.readlines()
            
#         func_defs = [line.strip() for line in lines if re.match(r'^\s*def\s+\w+\s*\(.*?\)\s*:', line)]
    
#         #extracting total number of variables and their types
#         try:
#             tree = make_ast(file)
#             functions, n_args = extract_fn_name_header(tree) #functions contains the total code for each function
            
#         except:
#              failed_file_num = failed_file_num +1
             
#              break
        
#         for item, num_args, fn_def in zip(functions, n_args, func_defs):
#             fn_name = re.match(r'^\s*def\s+(\w+)\s*\(', fn_def).group(1)
#             #make note, there is a bug where global variables are counted each time they are assigned...
#             variable_names, fn_calls = extract_calls_varnames(item, []) 
        
            
#             n_lines = len(ast.unparse(item).strip().splitlines())
#             proj_name = re.match(r'[^/]+/([^/]+)/[^/]+', file).group(1)
#             #print(proj_name)
        
#             #["file_name", "fn_name", "fn_sig", "line_count", "fn_called", "var_list", "fn_code"]
#             df.loc[len(df)] = [proj_name, file, fn_name, fn_def, n_lines, fn_calls, variable_names, str(ast.unparse(item))]
#             print(df.head())
#         return df
    

def find_functions(url, commit, short_name, file_path, path="../dataset_features/all_fn.csv"):
    #load_from_checkpoint(path)
    #print(file)
    file_name = re.split(r"/", file_path)[-1]
    #df_classes.loc[len(df_classes)] = [proj_name, file, , ]
    try:
        print("opening file")
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"read for fn failed: {e}"])
        print("ERROR")
        return
    
    func_defs = [line.strip() for line in lines if re.match(r'^\s*(?:async)?\s*def\s+\w+\s*\(.*?\).*?\s*:', line)]
    #edit this to spit back out function 
    
    #extracting total number of variables and their types
    try:
        print("making ast")
        tree = make_ast(file_path)
        classes, functions, n_args, name_list, arg_list= extract_fn_name_header(lines, tree) #functions contains the total code for each function
        
    except Exception as e:
            append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"make ast for fn failed: {e}"])
            print("ERROR")
            return
    
    if (len(func_defs) != len(functions) != len(n_args)):
        print("ERROR")
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"MISTAKE IN FN PARSING"])
        print(len(func_defs))
        print(len(functions))
        print(len(n_args))

    for cl, item, num_args, name, args in zip(classes, functions, n_args, name_list, arg_list):
        print("found item")
        fn_def = name + "(" + args + ")" #re.match(r'^\s*(?:async)?\s*def\s+(\w+)\s*\(', fn_def).group(1)
        #make note, there is a bug where global variables are counted each time they are assigned...
        variable_names, fn_calls = extract_calls_varnames(item, []) 
        
        n_lines = len(ast.unparse(item).strip().splitlines()) #This is where the problem is coming from :(
        #print(proj_name)

        # ["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "line_count", "fn_called", "var_list", "fn_code"]
        is_async = False
        if "async" in fn_def:
            is_async = True
        append_raw_csv(path, [url, commit, short_name, file_path, file_name, name, fn_def, num_args, n_lines, fn_calls, variable_names, cl, is_async])
        
        
    
def find_classes(url, commit, short_name, file_path, path="../dataset_features/all_class.csv"):
    file_name = re.split(r"/", file_path)[-1]
    #df_classes.loc[len(df_classes)] = [proj_name, file, , ]
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"read for classes failed: {e}"])
        print("ERROR")
        return          
    
    class_defs = [line.strip() for line in lines if re.match(r'^\s*class\s+(\w+)\s*(\([^)]*\))?:', line)] 
    try:
        tree = make_ast(file_path)
        classes, n_functions, node_classes = extract_classes(lines, tree)
    except Exception as e:
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"make ast for classes failed: {e}"])
        print("ERROR IN MAKE CLASS")
        return
    # return class_defs, classes, n_functions, node_classes, None

    for defs, item, node in zip(class_defs, classes, node_classes):
        n_lines = len(item.strip().splitlines())
        # ["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"]
        append_raw_csv(path, [url, commit, short_name, file_path, file_name, node.name, defs, n_lines, n_functions[node.name], item])

def find_all_calls(url, commit, short_name, file_path, path="../dataset_features/all_calls.csv"):
    file_name = re.split(r"/", file_path)[-1]
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"read for calls failed: {e}"])
        print("ERROR")
        return    
    
    try:
        tree = make_ast(file_path)
    except Exception as e:
        append_raw_csv("../dataset_features/clone_failures.csv", [url, file_name, file_path, f"make ast for calls failed: {e}"])
        print("ERROR IN MAKE CALL")
        return
        


    fn_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            #having some slight problems with call...
            fn_calls.append(ast.unparse(node)) 
    
    # ["url", "commit", "proj_name", "file_path", "file_name", "call_list"]
    append_raw_csv(path, [url, commit, short_name, file_path, file_name, fn_calls])