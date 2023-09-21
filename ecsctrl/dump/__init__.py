from typing import Generator, Tuple


def flat_dict_items(value, path="") -> Generator[Tuple[str, str], None, None]:
    def make_path(suffix):
        if not path:
            return str(suffix)
        return f"{path}.{suffix}"

    if isinstance(value, dict):
        for k, v in value.items():
            yield from flat_dict_items(v, make_path(k))

    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            yield from flat_dict_items(v, make_path(i))

    else:
        yield path, value


def generate_var_lut(vars):
    return {
        str(value): str(path)
        for path, value in sorted(
            list(flat_dict_items(vars)), key=lambda x: -len(str(x[1]))
        )
    }


def substitute_with_expressions(key: str, vars_lut) -> str:
    for var_value, var_name in vars_lut.items():
        if var_value in key:
            key = key.replace(var_value, r"{{ " + var_name + r" }}")
            return key
    return key
