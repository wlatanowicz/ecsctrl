from click.testing import CliRunner
from ecsctrl.cli import cli
from unittest import mock

from tests.data_files import get_file_path


@mock.patch("boto3.client")
def test_register(boto_mock):
    mocked_api_response = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:eu-west-1:327376576235:task-definition/ecs-test-web:36"
        }
    }
    client_mock = mock.Mock()
    client_mock.register_task_definition.return_value = mocked_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["task-definition", "register"]
    params += ["-j", get_file_path("tf-output.json")]
    params += [get_file_path("task-definition.yaml")]
    result = runner.invoke(cli, params, catch_exceptions=False)

    expected_api_params = {
        "family": "ecs-test-web",
        "tags": [
            {"key": "ManagedBy", "value": "ECSctrl"},
            {"key": "Environment", "value": "test"},
            {"key": "Project", "value": None},
            {"key": "Cluster", "value": "ecs-test"},
        ],
        "executionRoleArn": "arn:aws:iam::327376576235:role/ecs_task_execution_role",
        "taskRoleArn": "arn:aws:iam::327376576235:role/ecs_task_role",
        "networkMode": "awsvpc",
        "cpu": "512",
        "memory": "4096",
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx:",
                "memoryReservation": 512,
                "essential": True,
                "command": ["server"],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "ecs-test/web",
                        "awslogs-region": "eu-west-1",
                        "awslogs-stream-prefix": "web",
                        "awslogs-create-group": "true",
                    },
                },
                "portMappings": [{"containerPort": 80, "hostPort": 80}],
                "environment": [{"name": "DD_SERVICE_NAME", "value": "web"}],
            }
        ],
    }

    # print(client_mock.register_task_definition.call_args.kwargs)

    assert result.exit_code == 0
    client_mock.register_task_definition.assert_called_once_with(**expected_api_params)
