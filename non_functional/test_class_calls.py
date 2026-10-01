from mixed_effects_class import add_function_call_counts_with_imports, make_matches, make_imports_long
import pandas as pd
from ast import literal_eval



if __name__ == "__main__":
    # test_dict = {"index": 0,
    #             "url" : "https://github.com/kimeisele/steward-protocol",
    #             "commit": "0b42dd77b871dbab4687805569539ec8fd13257f",
    #             "proj_name": "steward-protocol",
    #             "file_path":"steward-protocol/vibe_core/cli/legacy.py",
    #             "file_name": "legacy.py",
    #             "imports": "{""pathlib: ['Path']"", 'warnings', 'os', 'subprocess', ""vibe_core.cartridges.system.envoy.provider: ['UniversalProvider']"", ""vibe_core.runtime_extensions: ['get_extension_status', 'install_semantic_extensions']"", 'time', 'json', 'sqlite3', ""datetime: ['datetime']"", ""vibe_core.boot_orchestrator: ['BootOrchestrator']"", 'argparse', 'hashlib', 'uuid', ""vibe_core.phoenix: ['get_config']"", 'logging', ""vibe_core.llm.local_llama_provider: ['download_default_model']"", ""vibe_core.runtime_extensions: ['get_extension_status']"", 'signal', ""vibe_core.config: ['load_config']"", 'sys', 'asyncio', 'traceback', ""typing: ['Any', 'Dict', 'Optional']""}"
    #                              }
    # test_imports = pd.DataFrame(test_dict, index=[0])

    df_imports = pd.read_csv("../dataset_features/imports.csv", names= ["url", "commit", "project", "file_path", "file", "imports"])
    df_imports.drop_duplicates(inplace=True)
    df_imports["imports"] = df_imports["imports"].apply(literal_eval)
    test_imports = df_imports #df_imports.iloc[df_imports["file_path"] == "steward-protocol/vibe_core/cli/legacy.py"]
    print(test_imports.head())

    # test_imports["imports"] = test_imports["imports"].apply(literal_eval)

    # fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])
    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'n_args', 'n_args': 'line_count','line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    # fn_df.drop_duplicates(inplace=True)
    # test_fn_df = pd.concat([fn_df.iloc[fn_df["fn_name"] == "install_semantic_extensions"], fn_df.iloc[fn_df["file_path"] == "Anubis/theia/autograde/autograde/exercise.py"], fn_df.iloc[fn_df["file_path"] == "Anubis/theia/autograde/autograde/exercise.py"]], ignore_index=True)
    # test_fn_df.drop_duplicates(inplace=True)

    # of times function is called
    df_calls = pd.read_csv("../dataset_features/all_calls.csv", names= ["url", "commit", "project", "file_path", "file", "calls"])
    df_calls.drop_duplicates(inplace=True)
    df_calls["calls"] = df_calls["calls"].apply(literal_eval)
    

    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)
    class_df["fn_count"] = class_df["fn_count"].apply(literal_eval)
    test_fn_df = pd.concat([class_df.iloc[class_df["class_name"] == "install_semantic_extensions"], class_df.iloc[class_df["file_path"] == "Anubis/theia/autograde/autograde/exercise.py"], class_df.iloc[class_df["url"] == "https://github.com/GusSand/Anubis"]], ignore_index=True)
    # test_fn_df.drop_duplicates(inplace=True)

    ##### AssertError on exceptions.py
    long_imports = make_imports_long(df_imports)
    print(long_imports)

    # functions_with_classes = add_origin_class_from_raw_text(
    # test_fn_df,
    # class_df,
    # project_col="url",
    # file_col="file_path",
    # fn_code_col="fn_code",
    # class_code_col="class_code",
    # class_name_col="class_name",
    # )
    print()
    print("test df")
    print(test_fn_df)

    calls_df = make_matches (
    test_fn_df,
    long_imports,
    project_col="url",
    class_col="class_name",
    class_file_col="file_path",
    imports_col="imports",     
    is_fn=False
)
    print("Calls")
    print(calls_df.head())

    


    
    # print(test_fn_df.head())
    calls_df = add_function_call_counts_with_imports(
    calls_df,
    df_calls,
    df_imports,
    project_col="url",
    function_col="class_name",
    calls_col="calls",
    file_col="file_path",
    imports_col="imports",
)
    
    print(calls_df)
    calls_df.to_csv("test_calls_class_df.csv")

    