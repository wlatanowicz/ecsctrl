from click.testing import CliRunner
import pytest
from ecsctrl.cli import cli
from unittest import mock

from tests.data_files import get_file_path


@mock.patch("boto3.client")
def test_update(boto_mock):
    mocked_api_response = {}
    client_mock = mock.Mock()
    client_mock.update_service.return_value = mocked_api_response
    boto_mock.return_value = client_mock

    runner = CliRunner()
    params = ["service", "update"]
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

    assert result.exit_code == 0
    client_mock.update_service.assert_called_once_with(**expected_api_params)
