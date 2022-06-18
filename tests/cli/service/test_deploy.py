from click.testing import CliRunner
from ecsctrl.cli import cli
from unittest import mock

from tests.data_files import get_file_path


@mock.patch("boto3.client")
def test_create(boto_mock):
    mocked_register_api_response = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:ap-northeast-1:448965722616:task-definition/web:123"
        }
    }
    mocked_describe_api_response = {"services": []}
    mocked_create_api_response = {"service": {"serviceArn": "arn"}}

    client_mock = mock.Mock()
    client_mock.register_task_definition.return_value = mocked_register_api_response
    client_mock.describe_services.return_value = mocked_describe_api_response
    client_mock.create_service.return_value = mocked_create_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["service", "deploy"]
    params += ["-j", get_file_path("tf-output.json")]
    params += [get_file_path("task-definition.yaml")]
    params += [get_file_path("service.yaml")]
    result = runner.invoke(cli, params, catch_exceptions=False)

    expected_service_api_params = {
        "serviceName": "web",
        "cluster": "ecs-test",
        "tags": [
            {"key": "ManagedBy", "value": "ECSctrl"},
            {"key": "Environment", "value": "test"},
            {"key": "Project", "value": None},
            {"key": "Cluster", "value": "ecs-test"},
        ],
        "enableECSManagedTags": True,
        "propagateTags": "TASK_DEFINITION",
        "desiredCount": 1,
        "launchType": "FARGATE",
        "loadBalancers": [
            {
                "targetGroupArn": "arn:aws:elasticloadbalancing:eu-west-1:327376576235:targetgroup/web/74c9f6cd45cab21",
                "containerName": "web",
                "containerPort": 80,
            }
        ],
        "taskDefinition": "arn:aws:ecs:ap-northeast-1:448965722616:task-definition/web:123",
        "deploymentConfiguration": {
            "maximumPercent": 200,
            "minimumHealthyPercent": 50,
            "deploymentCircuitBreaker": {"enable": True, "rollback": False},
        },
        "schedulingStrategy": "REPLICA",
        "deploymentController": {"type": "ECS"},
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "assignPublicIp": "DISABLED",
                "subnets": [
                    "subnet-935d90f551003a326",
                    "subnet-d1be0e0ff5ec21d55",
                    "subnet-280191fd831969f80",
                ],
                "securityGroups": ["sg-f962f180b78b1e1ce", "sg-694824e7b602c0b79"],
            }
        },
    }

    expected_task_definition_api_params = {
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

    assert result.exit_code == 0
    client_mock.describe_services.assert_called_once_with(
        cluster="ecs-test",
        services=[
            "web",
        ],
    )
    client_mock.register_task_definition.assert_called_once_with(
        **expected_task_definition_api_params
    )
    client_mock.create_service.assert_called_once_with(**expected_service_api_params)
    client_mock.update_service.assert_not_called()


@mock.patch("boto3.client")
def test_update(boto_mock):
    mocked_register_api_response = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:ap-northeast-1:448965722616:task-definition/web:123"
        }
    }
    mocked_describe_api_response = {"services": [{"serviceName": "web"}]}
    mocked_update_api_response = {"service": {"serviceArn": "arn"}}

    client_mock = mock.Mock()
    client_mock.register_task_definition.return_value = mocked_register_api_response
    client_mock.describe_services.return_value = mocked_describe_api_response
    client_mock.update_service.return_value = mocked_update_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["service", "deploy"]
    params += ["-j", get_file_path("tf-output.json")]
    params += [get_file_path("task-definition.yaml")]
    params += [get_file_path("service.yaml")]
    result = runner.invoke(cli, params, catch_exceptions=False)

    expected_service_api_params = {
        "service": "web",
        "cluster": "ecs-test",
        "enableECSManagedTags": True,
        "propagateTags": "TASK_DEFINITION",
        "desiredCount": 1,
        "loadBalancers": [
            {
                "targetGroupArn": "arn:aws:elasticloadbalancing:eu-west-1:327376576235:targetgroup/web/74c9f6cd45cab21",
                "containerName": "web",
                "containerPort": 80,
            }
        ],
        "taskDefinition": "arn:aws:ecs:ap-northeast-1:448965722616:task-definition/web:123",
        "deploymentConfiguration": {
            "maximumPercent": 200,
            "minimumHealthyPercent": 50,
            "deploymentCircuitBreaker": {"enable": True, "rollback": False},
        },
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "assignPublicIp": "DISABLED",
                "subnets": [
                    "subnet-935d90f551003a326",
                    "subnet-d1be0e0ff5ec21d55",
                    "subnet-280191fd831969f80",
                ],
                "securityGroups": ["sg-f962f180b78b1e1ce", "sg-694824e7b602c0b79"],
            }
        },
    }

    expected_task_definition_api_params = {
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

    assert result.exit_code == 0
    client_mock.describe_services.assert_called_once_with(
        cluster="ecs-test",
        services=[
            "web",
        ],
    )
    client_mock.register_task_definition.assert_called_once_with(
        **expected_task_definition_api_params
    )
    client_mock.update_service.assert_called_once_with(**expected_service_api_params)
    client_mock.create_service.assert_not_called()
