
import pandas as pd

def make_mask(df_source, df_files, name):  
    mask = (df_source[name])
    name_df = df_source[mask]
    url_set = set(name_df["url"])
    mask = (df_files["url"].isin(url_set))
    masked_files = df_files[mask] 
    return masked_files

if __name__ == "__main__":
    #setup
    fn_df = pd.read_csv("../dataset_features/all_fn.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "fn_name", "fn_sig", "n_args", "line_count", "fn_called", "var_list", "fn_code", "is_aysnc"])
    # fn_df =fn_df.rename(columns={'Unnamed: 0': 'url', 'url': 'commit', 'commit':'proj_name', 'proj_name': 'file_path', 'file_path':'file_name', 'file_name': 'fn_name', 'fn_name': 'fn_sig', 'fn_sig':'n_args', 'n_args': 'line_count','line_count':'fn_called', 'fn_called':'var_list', 'var_list':'fn_code', 'fn_code':'is_async', 'is_async': 'NaN'})
    fn_df.drop_duplicates(inplace=True)
    print(len(fn_df))
    source= pd.read_csv( "../main_exp_sheet.csv",  index_col=0)
    names = ["Vibecoding", "SideProject"]
    source.drop_duplicates(inplace=True)

    py_vc = make_mask(source, fn_df, names[0])
    py_sp = make_mask(source, fn_df, names[1])


    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    used_all = pd.concat([py_sp, py_vc], ignore_index=True)
    print(used_all.groupby("source").size())

    class_df = pd.read_csv("../dataset_features/all_class.csv", names=["url", "commit", "proj_name", "file_path", "file_name", "class_name", "class_sig", "line_count", "fn_count", "class_code"])
    class_df.drop_duplicates(inplace=True)
    print(len(class_df))




    py_vc = make_mask(source, class_df, names[0])
    py_sp = make_mask(source, class_df, names[1])


    py_sp["source"] = "SideProject"
    py_vc["source"] = "Vibecoding"

    used_all = pd.concat([py_sp, py_vc], ignore_index=True)
    print(used_all.groupby("source").size())


    df = pd.read_csv("../dataset_features/files_raw.csv", names=["url", "proj_name", "file_path", "file_name", "extn", "n_lines", "blank_lines", "char"])
    print(len(df))