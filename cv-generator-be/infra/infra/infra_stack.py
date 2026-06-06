from pathlib import Path

from aws_cdk import (
    CfnParameter,
    Duration,
    Fn,
    IgnoreMode,
    RemovalPolicy,
    SecretValue,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
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
        docker_excludes = (repo_root / ".dockerignore").read_text().splitlines()
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

        database_secret = rds.DatabaseSecret(
            self,
            "DatabaseSecret",
            username="cvapp",
        )
        database_secret.apply_removal_policy(RemovalPolicy.RETAIN)
        secret_resource = database_secret.node.default_child
        assert isinstance(secret_resource, secretsmanager.CfnSecret)
        # Keep the password secret created with the original database.
        secret_resource.override_logical_id(
            "CvGeneratorBeStackDatabaseSecret9E01CE843fdaad7efa858a3daf9490cf0a702aeb"
        )

        db = rds.DatabaseInstance(
            self,
            "DatabaseV2",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[rds_sg],
            credentials=rds.Credentials.from_password(
                "cvapp",
                database_secret.secret_value_from_json("password"),
            ),
            database_name="cvapp",
            allocated_storage=20,
            storage_type=rds.StorageType.GP3,
            removal_policy=RemovalPolicy.SNAPSHOT,
            deletion_protection=True,
            storage_encrypted=True,
            backup_retention=Duration.days(7),
            multi_az=False,
        )

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
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            assign_public_ip=True,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            public_load_balancer=True,
            security_groups=[ecs_sg],
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            # Give the container time to run Alembic migrations before the
            # load balancer starts health-checking it.
            health_check_grace_period=Duration.seconds(120),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    str(repo_root),
                    platform=ecr_assets.Platform.LINUX_AMD64,
                    exclude=docker_excludes,
                    ignore_mode=IgnoreMode.DOCKER,
                ),
                container_port=8000,
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
                        database_secret, "password"
                    ),
                    "CLERK_SECRET_KEY": ecs.Secret.from_secrets_manager(
                        clerk_secret_key
                    ),
                    "CLERK_JWT_KEY": ecs.Secret.from_secrets_manager(clerk_jwt_key),
                    "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(openai_api_key),
                    "STRIPE_SECRET_KEY": ecs.Secret.from_secrets_manager(stripe_secret_key),
                    "STRIPE_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(stripe_webhook_secret),
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
            healthy_threshold_count=2,
        )

        scaling = service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4,
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=60,
        )
