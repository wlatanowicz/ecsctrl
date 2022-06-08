import boto3
import json
import click


class BotoClient:
    def __init__(self, service, dry_run=False) -> None:
        self.dry_run = dry_run
        self.service = service
        self.client = None
        if not dry_run:
            self.client = boto3.client(service)

    def call(self, method, *args, **kwargs):
        if not self.dry_run:
            return getattr(self.client, method)(*args, **kwargs)
        else:
            json_spec = json.dumps(kwargs, indent=2)
            click.echo(f"🧸 BOTO: Would call `{self.service}:{method}` with {json_spec}")
            return self._dry_run_mocked_response(method, *args, **kwargs)

    def _dry_run_mocked_response(self, method, *args, **kwargs):
        if self.service == "ecs":
            if method == "register_task_definition":
                return {"taskDefinition": {"taskDefinitionArn": "N/A"}}
        if self.service == "ssm":
            if method == "put_parameter":
                return {"Version": 123}
        return {}
