from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_logs as logs,
)
from constructs import Construct


class CvGeneratorBeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).resolve().parents[2]

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=1,
        )

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
        )

        log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ApiService",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            public_load_balancer=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    str(repo_root),
                    platform=ecr_assets.Platform.LINUX_AMD64,
                ),
                container_port=8000,
                environment={
                    "ENV": "production",
                },
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="fastapi",
                    log_group=log_group,
                ),
            ),
        )

        service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
        )

        scaling = service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4,
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=60,
        )

        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=service.load_balancer.load_balancer_dns_name,
        )