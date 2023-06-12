import json
import sys
from functools import partial

import boto3
import click
from botocore.loaders import Loader
from botocore.model import ServiceModel
from botocore.validate import ParamValidator


class BotoClient:
    def __init__(self, service, dry_run=False) -> None:
        self.dry_run = dry_run
        self.service = service
        self.client = None
        if not dry_run:
            self.client = boto3.client(service)
        else:
            self.client = DryBotoClient(service)

    def call(self, method, *args, **kwargs):
        return getattr(self.client, method)(*args, **kwargs)


class DryBotoClient:
    def __init__(self, service) -> None:
        self.service = service
        self.service_model = self._load_service_model(service)

    def __getattr__(self, method):
        return partial(self._call, method)

    def _call(self, method, **params):
        json_params = json.dumps(params, indent=2)
        click.echo(f"🧸 BOTO: Would call `{self.service}:{method}` with {json_params}")
        self._validate_params(method, params)
        return self._dry_run_mocked_response(method, params)

    def _validate_params(self, method, parameters):
        operation_name = self._method_name_to_operation_name(method)
        operation_model = self.service_model.operation_model(operation_name)
        input_shape = operation_model.input_shape
        validator = ParamValidator()
        if input_shape is not None:
            report = validator.validate(parameters, input_shape)
            if report.has_errors():
                click.echo(
                    f"⛔️ BOTO: Function `{self.service}:{method}` parameter validation failed."
                )
                report_lines = report.generate_report().splitlines()
                for i, rl in enumerate(report_lines):
                    click.echo(f"🔴 Validation error {i+1}: " + rl)
                sys.exit(2)

        click.echo(
            f"✅ BOTO: Function `{self.service}:{method}` parameter validation passed."
        )

    def _dry_run_mocked_response(self, method, params):
        if self.service == "ecs":
            if method == "register_task_definition":
                return {"taskDefinition": {"taskDefinitionArn": "N/A"}}
            if method == "describe_services":
                return {"services": [{}]}
            if method == "update_service":
                return {"service": {"serviceArn": params["service"]}}
            if method == "create_service":
                return {"service": {"serviceArn": params["serviceName"]}}
        if self.service == "ssm":
            if method == "put_parameter":
                return {"Version": 123}
        if self.service == "batch":
            if method == "register_job_definition":
                return {"jobDefinitionArn": "N/A"}
        return {}

    def _load_service_model(self, service_name, api_version=None):
        loader = Loader()
        json_model = loader.load_service_model(
            service_name, "service-2", api_version=api_version
        )
        service_model = ServiceModel(json_model, service_name=service_name)
        return service_model

    def _method_name_to_operation_name(self, method_name: str):
        parts = method_name.split("_")
        return "".join([part.capitalize() for part in parts])
