from click.testing import CliRunner
from ecsctrl.cli import cli
from unittest import mock

from tests.data_files import get_file_path


@mock.patch("boto3.client")
def test_create(boto_mock):
    mocked_api_response = {"service": {"serviceArn": "arn"}}
    mocked_describe_api_response = {"services": []}

    client_mock = mock.Mock()
    client_mock.describe_services.return_value = mocked_describe_api_response
    client_mock.create_service.return_value = mocked_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["service", "create-or-update"]
    params += ["-j", get_file_path("tf-output.json")]
    params += [get_file_path("service.yaml")]
    result = runner.invoke(cli, params, catch_exceptions=False)

    expected_api_params = {
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
        "taskDefinition": "ecs-test-web",
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

    assert result.exit_code == 0
    client_mock.describe_services.assert_called_once_with(
        cluster="ecs-test",
        services=[
            "web",
        ],
    )
    client_mock.create_service.assert_called_once_with(**expected_api_params)
    client_mock.update_service.assert_not_called()


@mock.patch("boto3.client")
def test_update(boto_mock):
    mocked_api_response = {"service": {"serviceArn": "arn"}}
    mocked_describe_api_response = {"services": [{"serviceName": "web"}]}

    client_mock = mock.Mock()
    client_mock.describe_services.return_value = mocked_describe_api_response
    client_mock.update_service.return_value = mocked_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["service", "create-or-update"]
    params += ["-j", get_file_path("tf-output.json")]
    params += [get_file_path("service.yaml")]
    result = runner.invoke(cli, params, catch_exceptions=False)

    expected_api_params = {
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
        "taskDefinition": "ecs-test-web",
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

    print(client_mock.update_service.call_args.kwargs)

    assert result.exit_code == 0
    client_mock.describe_services.assert_called_once_with(
        cluster="ecs-test",
        services=[
            "web",
        ],
    )
    client_mock.update_service.assert_called_once_with(**expected_api_params)
    client_mock.create_service.assert_not_called()
