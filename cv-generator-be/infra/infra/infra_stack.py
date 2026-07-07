from pathlib import Path

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Fn,
    RemovalPolicy,
    SecretValue,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_logs as logs,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class CvGeneratorBeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).resolve().parents[2]
        frontend_url = CfnParameter(
            self,
            "FrontendUrl",
            type="String",
            default="https://hireable.vericodehq.com",
            description="Canonical frontend URL used for Stripe return URLs and Clerk authorized parties.",
        )
        stripe_pro_price_id = CfnParameter(
            self,
            "StripeProPriceId",
            type="String",
            allowed_pattern="^price_.+",
            description="Stripe live recurring Price ID for the Pro subscription.",
        )

        # No NAT gateways (~$35/mo saved). The API tasks run in the public
        # subnets with a public IP for outbound calls (OpenAI, Stripe, Clerk,
        # ECR, Secrets Manager); the private subnets keep the same CIDRs so the
        # existing RDS instance is not replaced — they simply lose their NAT
        # route, which RDS never needed.
        # The subnet groups deliberately keep the default names ("Public",
        # "Private") so the existing subnets keep their logical IDs and CIDRs
        # and are updated in place rather than replaced.
        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            ],
        )

        # Security group for ECS Fargate tasks
        ecs_sg = ec2.SecurityGroup(
            self,
            "EcsSg",
            vpc=vpc,
            description="CV Generator API tasks",
        )

        # Security group for RDS — only accepts connections from ECS tasks
        rds_sg = ec2.SecurityGroup(
            self,
            "RdsSg",
            vpc=vpc,
            description="CV Generator RDS instance",
        )
        rds_sg.add_ingress_rule(ecs_sg, ec2.Port.tcp(5432))

        cloudshell_sg = ec2.SecurityGroup(
            self,
            "CloudShellSg",
            vpc=vpc,
            description="CloudShell access to RDS for manual queries",
        )

        rds_sg.add_ingress_rule(
            cloudshell_sg,
            ec2.Port.tcp(5432),
            "Allow CloudShell to connect to PostgreSQL",
        )

        # RDS PostgreSQL 16 — credentials are auto-generated in Secrets Manager
        db = rds.DatabaseInstance(
            self,
            "Database",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            # Graviton burstable — same size as t3.micro but cheaper per hour.
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            # With nat_gateways=0 the VPC's "Private" subnets become isolated
            # (same names and CIDRs, so the existing instance stays in place).
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[rds_sg],
            credentials=rds.Credentials.from_generated_secret("cvapp"),
            database_name="cvapp",
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            storage_encrypted=True,
            storage_type=rds.StorageType.GP3,
            backup_retention=Duration.days(0),
            multi_az=False,
        )

        CfnOutput(
            self,
            "CloudShellSecurityGroupId",
            value=cloudshell_sg.security_group_id,
        )

        assert db.secret is not None, "RDS secret must exist when using from_generated_secret"

        # Placeholder secrets for external service keys.
        # Update these in the AWS Secrets Manager console before the app can
        # authenticate users or generate CVs.  RemovalPolicy.RETAIN keeps
        # operator-supplied values safe across stack redeployments.
        clerk_secret_key = secretsmanager.Secret(
            self,
            "ClerkSecretKey",
            secret_name="cv-generator/clerk-secret-key",
            description="Clerk secret key — replace PLACEHOLDER before using auth",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )
        clerk_jwt_key = secretsmanager.Secret(
            self,
            "ClerkJwtKey",
            secret_name="cv-generator/clerk-jwt-key",
            description="Clerk JWT public key — replace PLACEHOLDER before using auth",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )
        openai_api_key = secretsmanager.Secret(
            self,
            "OpenAiApiKey",
            secret_name="cv-generator/openai-api-key",
            description="OpenAI API key — replace PLACEHOLDER before generating CVs",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )
        stripe_secret_key = secretsmanager.Secret(
            self,
            "StripeSecretKey",
            secret_name="cv-generator/stripe-secret-key",
            description="Stripe secret key — replace PLACEHOLDER before billing is enabled",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )
        stripe_webhook_secret = secretsmanager.Secret(
            self,
            "StripeWebhookSecret",
            secret_name="cv-generator/stripe-webhook-secret",
            description="Stripe webhook signing secret — replace PLACEHOLDER before billing is enabled",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )
        cloudflare_tunnel_token = secretsmanager.Secret(
            self,
            "CloudflareTunnelToken",
            secret_name="cv-generator/cloudflare-tunnel-token",
            description="Cloudflare Tunnel token — replace PLACEHOLDER so the API is reachable at api.vericodehq.com",
            secret_string_value=SecretValue.unsafe_plain_text("PLACEHOLDER"),
            removal_policy=RemovalPolicy.RETAIN,
        )

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            enable_fargate_capacity_providers=True,
        )

        log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Ingress is a Cloudflare Tunnel sidecar instead of an ALB (~$20/mo
        # saved): cloudflared makes an outbound connection to Cloudflare, which
        # terminates TLS for api.vericodehq.com and forwards requests to the
        # API container over the task-local network.
        task_definition = ecs.FargateTaskDefinition(
            self,
            "ApiTaskDef",
            cpu=256,
            memory_limit_mib=1024,
        )

        api_container = task_definition.add_container(
            "Api",
            image=ecs.ContainerImage.from_asset(
                str(repo_root),
                platform=ecr_assets.Platform.LINUX_AMD64,
            ),
            # Run DB migrations before starting the server so the schema is
            # always up to date on every deployment.
            command=[
                "sh",
                "-c",
                "alembic -c /app/app/alembic.ini upgrade head && "
                "uvicorn app.main:app --host 0.0.0.0 --port 8000",
            ],
            environment={
                "ENV": "production",
                "DB_HOST": db.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "cvapp",
                "DB_USER": "cvapp",
                # Comma-separated list of allowed CORS / Clerk origins.
                # Add your Cloudflare Pages URL here, e.g.:
                #   "https://cv-generator.pages.dev,http://localhost:5173"
                "CLERK_AUTHORIZED_PARTIES": Fn.join(
                    ",",
                    ["http://localhost:5173", frontend_url.value_as_string],
                ),
                "FRONTEND_URL": frontend_url.value_as_string,
                "STRIPE_PRO_PRICE_ID": stripe_pro_price_id.value_as_string,
            },
            secrets={
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(
                    db.secret, "password"
                ),
                "CLERK_SECRET_KEY": ecs.Secret.from_secrets_manager(
                    clerk_secret_key
                ),
                "CLERK_JWT_KEY": ecs.Secret.from_secrets_manager(clerk_jwt_key),
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(openai_api_key),
                "STRIPE_SECRET_KEY": ecs.Secret.from_secrets_manager(stripe_secret_key),
                "STRIPE_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(stripe_webhook_secret),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="fastapi",
                log_group=log_group,
            ),
            # Replaces the ALB health check: ECS restarts the task if the API
            # stops answering. The generous start period covers Alembic
            # migrations on boot.
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)\"",
                ],
                interval=Duration.seconds(30),
                start_period=Duration.seconds(120),
            ),
        )
        api_container.add_port_mappings(ecs.PortMapping(container_port=8000))

        tunnel_container = task_definition.add_container(
            "Cloudflared",
            image=ecs.ContainerImage.from_registry("cloudflare/cloudflared:latest"),
            command=["tunnel", "--no-autoupdate", "run"],
            secrets={
                "TUNNEL_TOKEN": ecs.Secret.from_secrets_manager(
                    cloudflare_tunnel_token
                ),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="cloudflared",
                log_group=log_group,
            ),
        )
        # Only open the tunnel once the API answers health checks, so rolling
        # deployments never route traffic to a task that isn't ready.
        tunnel_container.add_container_dependencies(
            ecs.ContainerDependency(
                container=api_container,
                condition=ecs.ContainerDependencyCondition.HEALTHY,
            )
        )

        service = ecs.FargateService(
            self,
            "ApiService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            security_groups=[ecs_sg],
            # Public subnet + public IP gives the task free outbound internet
            # (no NAT). Nothing listens publicly — the security group has no
            # inbound rules; all ingress arrives through the tunnel.
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            assign_public_ip=True,
            # Fargate Spot is ~70% cheaper. Worst case a task is reclaimed
            # with a 2-minute warning and ECS immediately starts a
            # replacement — acceptable for this workload.
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=1,
                ),
            ],
            # Zero-downtime deploys: start the new task before stopping the
            # old one (both tunnel replicas can be connected at once).
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

        CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
        )

        CfnOutput(
            self,
            "ServiceName",
            value=service.service_name,
        )

        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=db.db_instance_endpoint_address,
        )
