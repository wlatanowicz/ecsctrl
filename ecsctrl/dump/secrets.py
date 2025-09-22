import re
from . import substitute_with_expressions


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


def dump_secrets(ssm, filter=None):
    for parameter in list_secrets(ssm):
        parameter_name = parameter["Name"]
        response = ssm.call(
            "get_parameter",
            Name=parameter_name,
            WithDecryption=True,
        )

        if filter is None or re.match(filter, parameter_name):
            yield parameter_name, response["Parameter"]["Value"]


def render_dumped_secrets(click, secrets, vars_lut, target_file):
    with open(target_file, "w") as f:
        for name, value in secrets:
            key = substitute_with_expressions(name, vars_lut)
            secret_line = f"{key}: {value}"
            f.write(secret_line + "\n")
            click.echo(f"🔑 Dumped secret {key}.")
