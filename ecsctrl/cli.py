from email.policy import default
import os
import click
import re

from ecsctrl.loader import VarsLoader

from .boto_client import BotoClient
from .yaml_converter import yaml_file_to_dict

from .service_updater import TaskDefinitionServiceUpdater, WaitForUpdate, ServiceUpdater


def check_var(ctx, param, value):
    for v in value:
        if not re.match("^[^=]+=.*$", v):
            raise click.BadParameter(
                f"'{v}'. Variable has to be in format variable=value"
            )
    return value


@click.group()
@click.option(
    "--dry-run", is_flag=True, default=False, help="Do not call actual AWS API"
)
@click.pass_context
def cli(ctx, dry_run):
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["boto_client"] = BotoClient("ecs", dry_run=dry_run)


@cli.group(name="task-definition")
@click.pass_context
def task_definition(ctx):
    pass


# fmt: off
@task_definition.command()
@click.argument("spec-file", type=str)
@click.option("--env-file", "-e", multiple=True, type=str, help="Path to env-style file with variables")
@click.option("--json-file", "-j", multiple=True, type=str, help="Path to json file with variable")
@click.option("--var", "-v", multiple=True, type=str, callback=check_var, help="Single variable in format name=value")
@click.option("--sys-env/--no-sys-env", is_flag=True, default=False, help="Uses system env as a source for template variables")
@click.option("--update-services-in-cluster", "-c", multiple=True, type=str, help="Updates all services deployed with this task in a particular cluster")
@click.option("--wait", "-w", is_flag=True, help="Waits for services to finish update")
@click.pass_context
# fmt: on
def register(
    ctx,
    spec_file,
    env_file,
    json_file,
    var,
    sys_env,
    update_services_in_cluster,
    wait,
):
    vars = VarsLoader(env_file, var, json_file, sys_env).load()
    spec = yaml_file_to_dict(spec_file, vars)
    task_family = spec.get("family", "N/A")
    click.echo(f"🗂 Registering task definition {task_family}.")
    response = ctx.obj["boto_client"].call("register_task_definition", **spec)
    task_definition_arn = response["taskDefinition"]["taskDefinitionArn"]
    click.echo(f"\t✅ done, task definition arn: {task_definition_arn}.")

    if update_services_in_cluster and not ctx.obj["dry_run"]:
        updated_services = {}

        for cluster_name in update_services_in_cluster:
            updater = TaskDefinitionServiceUpdater(
                ctx.obj["boto_client"], task_definition_arn, cluster_name
            )
            updated_services_in_cluster = updater.update()
            updated_services[cluster_name] = updated_services_in_cluster

        if wait:
            waiter = WaitForUpdate(ctx.obj["boto_client"], updated_services)
            waiter.wait_for_all()


@cli.group(name="service")
@click.pass_context
def service(ctx):
    pass


# fmt: off
@service.command()
@click.argument("spec-file", type=str)
@click.option("--env-file", "-e", multiple=True, type=str, help="Path to env-style file with variables")
@click.option("--json-file", "-j", multiple=True, type=str, help="Path to json file with variable")
@click.option("--var", "-v", multiple=True, type=str, callback=check_var, help="Single variable in format name=value")
@click.option("--sys-env/--no-sys-env", is_flag=True, default=False, help="Uses system env as a source for template variables")
@click.option("--wait", "-w", is_flag=True, help="Waits for services to finish creation")
@click.pass_context
# fmt: on
def create(ctx, spec_file, env_file, json_file, var, sys_env, wait):
    vars = VarsLoader(env_file, var, json_file, sys_env).load()
    spec = yaml_file_to_dict(spec_file, vars)
    service_name = spec.get("serviceName", "N/A")
    click.echo(f"🏸 Creating service {service_name}.")
    ctx.obj["boto_client"].call("create_service", **spec)
    click.echo("\t✅ done.")

    if wait:
        waiter = WaitForUpdate(ctx.obj["boto_client"], [service_name])
        waiter.wait_for_all()


# fmt: off
@service.command()
@click.argument("spec-file", type=str)
@click.option("--env-file", "-e", multiple=True, type=str, help="Path to env-style file with variables")
@click.option("--json-file", "-j", multiple=True, type=str, help="Path to json file with variable")
@click.option("--var", "-v", multiple=True, type=str, callback=check_var, help="Single variable in format name=value")
@click.option("--sys-env/--no-sys-env", is_flag=True, default=False, help="Uses system env as a source for template variables")
@click.option("--wait", "-w", is_flag=True, help="Waits for services to finish update")
@click.pass_context
# fmt: on
def update(ctx, spec_file, env_file, json_file, var, sys_env, wait):
    vars = VarsLoader(env_file, var, json_file, sys_env).load()
    spec = yaml_file_to_dict(spec_file, vars)
    service_name = spec.get("serviceName", "N/A")
    click.echo(f"🏸 Updating service {service_name}.")
    updater = ServiceUpdater()
    spec = updater.make_update_payload(spec)
    ctx.obj["boto_client"].call("update_service", **spec)
    click.echo("\t✅ done.")

    if wait:
        waiter = WaitForUpdate(ctx.obj["boto_client"], [service_name])
        waiter.wait_for_all()


# fmt: off
@service.command("create-or-update")
@click.argument("spec-file", type=str)
@click.option("--env-file", "-e", multiple=True, type=str, help="Path to env-style file with variables")
@click.option("--json-file", "-j", multiple=True, type=str, help="Path to json file with variable")
@click.option("--var", "-v", multiple=True, type=str, callback=check_var, help="Single variable in format name=value")
@click.option("--sys-env/--no-sys-env", is_flag=True, default=False, help="Uses system env as a source for template variables")
@click.option("--wait", "-w", is_flag=True, help="Waits for services to finish update")
@click.pass_context
# fmt: on
def create_or_update(ctx, spec_file, env_file, json_file, var, sys_env, wait):
    vars = VarsLoader(env_file, var, json_file, sys_env).load()
    spec = yaml_file_to_dict(spec_file, vars)
    service_name = spec.get("serviceName", "N/A")

    response = ctx.obj["boto_client"].call(
        "describe_services",
        cluster=spec["cluster"],
        services=[service_name],
    )
    service_exists = len(response["services"]) > 0

    if service_exists:
        click.echo(f"🏸 Updating service {service_name}.")
        updater = ServiceUpdater()
        spec = updater.make_update_payload(spec)
        ctx.obj["boto_client"].call("update_service", **spec)
        click.echo("\t✅ done.")
    else:
        click.echo(f"🏸 Creating service {service_name}.")
        ctx.obj["boto_client"].call("create_service", **spec)
        click.echo("\t✅ done.")

    if wait:
        waiter = WaitForUpdate(ctx.obj["boto_client"], [service_name])
        waiter.wait_for_all()


@cli.group(name="secrets")
@click.pass_context
def secrets(ctx):
    pass


# fmt: off
@secrets.command()
@click.argument("spec-file", type=str)
@click.option("--env-file", "-e", multiple=True, type=str, help="Path to env-style file with variables")
@click.option("--json-file", "-j", multiple=True, type=str, help="Path to json file with variable")
@click.option("--var", "-v", multiple=True, type=str, callback=check_var, help="Single variable in format name=value")
@click.option("--sys-env/--no-sys-env", is_flag=True, default=False, help="Uses system env as a source for template variables")
@click.pass_context
# fmt: on
def store(ctx, spec_file, env_file, json_file, var, sys_env):
    vars = VarsLoader(env_file, var, json_file, sys_env).load()
    spec = yaml_file_to_dict(spec_file, vars)
    ssm = BotoClient("ssm", dry_run=ctx.obj["boto_client"].dry_run)

    for secret_name, value in spec.items():
        ssm_params = {
            "Name": secret_name,
            "Value": value,
            "Type": "SecureString",
        }
        click.echo(f"🔑 Storing secret {secret_name}.")
        response = ssm.call("put_parameter", **ssm_params)
        click.echo(f"\t✅ done, parameter version: {response['Version']}")
