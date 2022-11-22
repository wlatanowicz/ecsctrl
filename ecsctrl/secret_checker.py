from typing import List
from boto_client import BotoClient
import click


class SecretChecker:
    def __init__(self, dry_run) -> None:
        self.client = BotoClient(dry_run)

    def check(self, task_definition_spec):
        missing_secrets = self.find_missing_secrets(task_definition_spec)
        if missing_secrets:
            missing_secrets_str = ", ".join(missing_secrets)
            click.echo(f"🔴🔑 Missing secrets required by task definition: {missing_secrets_str}")

    def find_missing_secrets(self, task_definition_spec) -> List[str]:
        missing_secrets = []
        all_secrets = self.get_secret_names(task_definition_spec)
        for secret in all_secrets:
            if not self.secret_exists(secret):
                missing_secrets.append(secret)
        return missing_secrets

    def secret_exists(self, name):
        try:
            secret = self.describe_secret(name)
            return secret["Name"] == name
        except IndexError:
            return False

    def get_secret_names(self, task_definition_spec):
        names = []
        try:
            container_definitions = task_definition_spec["containerDefinitions"]
        except KeyError:
            return names

        for container_definition in container_definitions:
            try:
                secret_definitons = container_definition["secrets"]
            except KeyError:
                continue

            for secret_definition in secret_definitons:
                names.append(secret_definition["valueFrom"])

        return names

    def describe_secret(self, name):
        return self.client(
            "describe_parameters",
            ParameterFilters={
                "Key": "Name",
                "Option": "Equals",
                "Values": [name],
            },
        )["Parameters"][0]
