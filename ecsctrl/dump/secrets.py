import re
from . import substitute_with_expressions
from dataclasses import dataclass
from typing import Generator, Sequence


@dataclass
class Parameter:
    name: str
    value: str
    type: str


def list_secrets(ssm):
    should_fetch = True
    next_token = None

    while should_fetch:
        kwargs = {}
        if next_token:
            kwargs["NextToken"] = next_token
        response = ssm.call("describe_parameters", **kwargs)
        next_token = response.get("NextToken")
        should_fetch = bool(next_token)

        for parameter in response["Parameters"]:
            yield parameter


def dump_secrets(ssm, filter=None) -> Generator[Parameter, None, None]:
    for parameter in list_secrets(ssm):
        parameter_name = parameter["Name"]
        if filter is None or re.match(filter, parameter_name):
            response = ssm.call(
                "get_parameter",
                Name=parameter_name,
                WithDecryption=True,
            )

            yield Parameter(
                name=parameter_name,
                value=response["Parameter"]["Value"],
                type=response["Parameter"]["Type"],
            )


def render_dumped_secrets(click, secrets: Sequence[Parameter], vars_lut, target_file):
    with open(target_file, "w") as f:
        for parameter in secrets:
            key, secret_text = rended_single_secret(parameter, vars_lut)
            f.write(f"# Dumped from `{parameter.name}`:\n")
            f.write(secret_text)
            f.write(f"\n")
            click.echo(f"🔑 Dumped secret {parameter.name} as {key}.")


def rended_single_secret(parameter: Parameter, vars_lut):
    name = parameter.name
    key = substitute_with_expressions(name, vars_lut)
    if parameter.type == "SecureString":
        secret_text = render_simple_secret(key, parameter)
    else:
        secret_text = render_complex_secret(key, parameter)
    return key, secret_text


def render_simple_secret(key, parameter):
    value = render_value(parameter.value, 1)
    secret_text = f"{key}: {value}\n"
    return secret_text


def render_complex_secret(key, parameter):
    value = render_value(parameter.value, 2)
    secret_text = f"{key}:\n"
    secret_text += f"  Type: {parameter.type}\n"
    secret_text += f"  Value: {value}\n"
    return secret_text


def render_value(value: str, indent: int) -> str:
    if "\n" in value:
        last_nl = "-"
        if value.endswith("\n"):
            last_nl = ""
        result_lines = [f"|{last_nl}"]
        for line in value.split("\n"):
            result_lines.append(("  " * indent) + line)
        return "\n".join(result_lines)

    return value
