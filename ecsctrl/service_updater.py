import re
from time import sleep, time
from typing import Dict, List
from datetime import datetime, timezone
import sys
import math
import os
import click


class TaskDefinitionServiceUpdater:
    def __init__(
        self, boto_client, task_definition_arn: str, cluster_name: str
    ) -> None:
        self.boto_client = boto_client
        self.task_definition_arn = task_definition_arn
        self.cluster_name = cluster_name
        self.task_definition_family = re.findall(
            r".+\/(.+)\:\d+?", self.task_definition_arn
        )

    def update(self) -> List[str]:
        services = self.find_services_to_update()
        for service_arn, service_name in services:
            click.echo(f"🏗 Updating service {service_name}.")
            self.update_service(service_arn)
            click.echo("\t✅ done.")
        return services

    def find_services_to_update(self) -> List[str]:
        services = []

        kwargs = {}
        while True:
            list_response = self.boto_client.call(
                "list_services", maxResults=10, cluster=self.cluster_name, **kwargs
            )
            describe_response = self.boto_client.call(
                "describe_services",
                cluster=self.cluster_name,
                services=list_response["serviceArns"],
            )

            for service in describe_response["services"]:
                task_definition = service["taskDefinition"]
                service_task_name = re.findall(r".+\/(.+)\:\d+?", task_definition)
                if service_task_name == self.task_definition_family:
                    services.append((service["serviceArn"], service["serviceName"]))
            if list_response.get("nextToken"):
                kwargs["nextToken"] = list_response["nextToken"]
            else:
                break

        return services

    def update_service(self, service_arn: str):
        self.boto_client.call(
            "update_service",
            taskDefinition=self.task_definition_arn,
            cluster=self.cluster_name,
            service=service_arn,
        )


class WaitForUpdate:
    def __init__(self, boto_client, services_in_clusters: Dict[str, str]) -> None:
        self.boto_client = boto_client
        self.services_in_clusters = services_in_clusters

    def describe_all_services(self):
        described_services = []
        for cluster, services in self.services_in_clusters.items():
            arns = [service_arn for service_arn, service_name in services]
            while arns:
                response = self.boto_client.call(
                    "describe_services", cluster=cluster, services=arns[:10]
                )
                for service_description in response["services"]:
                    service_description["clusterName"] = cluster
                    described_services.append(service_description)

                arns = arns[10:]

        return described_services

    def wait_for_all(self):
        total_failures = 1
        total_critical = False
        timeout = 600
        wait_time = 60
        deadline = time() + timeout
        start_time = time()

        while total_failures and not total_critical:
            total_failures = 0
            total_critical = False
            services = self.describe_all_services()
            for service in services:
                failures, critical = self.check_single_service(service)
                total_failures += failures
                total_critical = total_critical or critical
                sleep(0.2)

            if total_critical:
                click.echo("💀 Oh no! Deployment failed. Exiting.")
                sys.exit(1)

            if total_failures == 0:
                click.echo("🍾 All done.")
                return
            else:
                if time() > deadline:
                    click.echo("💀 Oh no! Timeout reached. Exiting.")
                    sys.exit(1)
                else:
                    click.echo(
                        f"⏳ Waiting for things to settle ({total_failures} check/s/ failed)"
                    )

                    pause_time = time()
                    if not os.environ.get("CI"):
                        animation = "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"
                        for i in range(wait_time * 10):
                            sys.stdout.write("\r" + animation[i % len(animation)])
                            sys.stdout.flush()
                            sleep(0.1)
                        sys.stdout.write("\r")
                        sys.stdout.flush()
                    else:
                        sleep(wait_time)

                    time_passed = math.floor(time() - start_time)
                    resumed_after = math.floor(time() - pause_time)
                    click.echo("")
                    click.echo(
                        f"🚀 Resuming after {resumed_after}s ({time_passed}s passed from the beginning) "
                    )

    def check_single_service(self, service_description):
        failures = 0

        cluster_name = service_description["clusterName"]
        service_name = service_description["serviceName"]
        service_task_definition = service_description["taskDefinition"]
        service_task_desired_count = service_description["desiredCount"]
        service_task_running_count = service_description["runningCount"]
        service_task_pending_count = service_description["pendingCount"]

        min_task_age = 60  # @TODO get from cli arguments

        deployments = service_description["deployments"]
        primary_deployment = [d for d in deployments if d["status"] == "PRIMARY"][0]

        click.echo("🔍 Running checks")
        click.echo(f"🌎 Cluster: {cluster_name}")
        click.echo(f"🏓 Service: {service_name}")

        click.echo(f"\t👮‍♀️ Desired task count: {service_task_desired_count}")

        if service_task_desired_count == service_task_running_count:
            click.echo(f"\t😀 Running task count: {service_task_running_count}")
        else:
            click.echo(f"\t😱 Running task count: {service_task_running_count}")
            failures += 1

        if service_task_pending_count == 0:
            click.echo(f"\t😀 Pending task count: {service_task_pending_count}")
        else:
            click.echo(f"\t😱 Pending task count: {service_task_pending_count}")
            failures += 1

        click.echo(f"\t👮🏽‍♂️ Desired task definition: {service_task_definition}")

        task_arns = self.boto_client.call(
            "list_tasks", serviceName=service_name, cluster=cluster_name
        )["taskArns"]

        for task_arn in task_arns:
            task = self.boto_client.call(
                "describe_tasks", tasks=[task_arn], cluster=cluster_name
            )["tasks"][0]

            task_age = int(
                datetime.now().replace(tzinfo=timezone.utc).timestamp()
                - task["createdAt"].replace(tzinfo=timezone.utc).timestamp()
            )
            task_task_definition = task["taskDefinitionArn"]

            if task_age >= min_task_age:
                click.echo(f"\t😀 Task {task_arn} age is OK")
            else:
                click.echo(
                    f"\t😱 Task {task_arn} is to young ({task_age}s, {min_task_age}s minimum)"
                )
                failures += 1

            if task_task_definition == service_task_definition:
                click.echo(f"\t😀 Task {task_arn} task definition is OK")
            else:
                click.echo(
                    f"\t😱 Task {task_arn} task definition is {task_task_definition}"
                )
                failures += 1

        if primary_deployment["rolloutState"] == "COMPLETED":
            click.echo("\t😀 Primary deployment completed.")
        elif primary_deployment["rolloutState"] == "IN_PROGRESS":
            click.echo("\t🧑‍🔧 Primary deployment is still in progress.")
        elif primary_deployment["rolloutState"] == "FAILED":
            click.echo("\t💀 Oh no! Primary deployment failed.")
            failures += 1
            return failures, True

        if not failures:
            click.echo("\t✅ Service updated successfully.")

        return failures, False


class ServiceUpdater:
    CREATE_TO_UPDATE = {
        "serviceName": "service",
    }

    ALLOWED_FIELDS = [
        "cluster",
        "service",
        "desiredCount",
        "taskDefinition",
        "capacityProviderStrategy",
        "deploymentConfiguration",
        "networkConfiguration",
        "placementConstraints",
        "placementStrategy",
        "platformVersion",
        "forceNewDeployment",
        "healthCheckGracePeriodSeconds",
        "enableExecuteCommand",
        "enableECSManagedTags",
        "loadBalancers",
        "propagateTags",
        "serviceRegistries",
    ]

    def make_update_payload(self, create_payload):
        payload_with_translated_fields = {
            self.CREATE_TO_UPDATE.get(k, k): v for k, v in create_payload.items()
        }

        update_payload = {
            k: v
            for k, v in payload_with_translated_fields.items()
            if k in self.ALLOWED_FIELDS
        }

        return update_payload
