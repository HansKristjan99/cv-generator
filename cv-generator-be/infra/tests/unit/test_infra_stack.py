import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from infra.infra_stack import CvGeneratorBeStack


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    app = core.App()
    stack = CvGeneratorBeStack(app, "infra")
    return assertions.Template.from_stack(stack)


def test_no_nat_gateway_or_load_balancer(template: assertions.Template) -> None:
    # The two biggest fixed costs were removed: ingress goes through a
    # Cloudflare Tunnel sidecar and egress through public-subnet task IPs.
    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 0)


def test_service_runs_one_task_on_fargate_spot(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::ECS::Service",
        {
            "DesiredCount": 1,
            "CapacityProviderStrategy": [
                {"CapacityProvider": "FARGATE_SPOT", "Weight": 1}
            ],
        },
    )


def test_task_is_right_sized(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {"Cpu": "256", "Memory": "1024"},
    )


def test_database_uses_graviton_and_gp3(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {"DBInstanceClass": "db.t4g.micro", "StorageType": "gp3"},
    )


def test_tunnel_sidecar_waits_for_healthy_api(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        assertions.Match.object_like(
            {
                "ContainerDefinitions": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Name": "Cloudflared",
                                "DependsOn": [
                                    {"Condition": "HEALTHY", "ContainerName": "Api"}
                                ],
                            }
                        )
                    ]
                )
            }
        ),
    )
