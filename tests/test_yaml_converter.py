from ecsctrl.yaml_converter import TASK_DEFINITION, yaml_data_to_dict


def test_yaml_data_to_dict():
    in_yaml = {
        "containerDefinitions": [
            {
                "environment": {
                    "A": "b",
                }
            }
        ]
    }
    expected_out_dict = {
        "containerDefinitions": [
            {
                "environment": [
                    {
                        "name": "A",
                        "value": "b",
                    }
                ]
            }
        ]
    }

    out_dict = yaml_data_to_dict(in_yaml, TASK_DEFINITION)

    assert expected_out_dict == out_dict
