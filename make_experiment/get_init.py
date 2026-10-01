import ast

def get_call_name(func):
    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        base = get_call_name(func.value)
        if base is None:
            return func.attr
        return f"{base}.{func.attr}"

    return None


def find_class_instantiations(code, known_classes):
    tree = ast.parse(code)
    instances = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = get_call_name(node.func)

            if call_name is None:
                continue

            class_name = call_name.split(".")[-1]

            if class_name in known_classes:
                instances.append({
                    "class_name": class_name,
                    "call_name": call_name,
                    "line": node.lineno,
                    "col": node.col_offset,
                })

    return instances
def get_init ():
    known_classes = set(classes_df["class_name"])

    functions_df["class_instantiations"] = functions_df["fn_code"].apply(
    lambda code: find_class_instantiations(code, known_classes)
    )