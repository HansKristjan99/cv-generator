import aws_cdk as cdk
import aws_cdk.assertions as assertions

from infra.infra_stack import CvGeneratorBeStack


def synthesized_template() -> assertions.Template:
    app = cdk.App()
    stack = CvGeneratorBeStack(app, "CvGeneratorBeStack")
    return assertions.Template.from_stack(stack)


def test_nat_gateway_is_removed_and_tasks_use_public_subnets() -> None:
    template = synthesized_template()

    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.resource_count_is("AWS::EC2::Route", 2)
    template.has_resource_properties(
        "AWS::ECS::Service",
        {
            "DeploymentConfiguration": {
                "DeploymentCircuitBreaker": {
                    "Enable": True,
                    "Rollback": True,
                },
                "MinimumHealthyPercent": 100,
            },
            "NetworkConfiguration": {
                "AwsvpcConfiguration": {
                    "AssignPublicIp": "ENABLED",
                    "Subnets": [
                        {"Ref": "VpcPublicSubnet1Subnet5C2D37C4"},
                        {"Ref": "VpcPublicSubnet2Subnet691E08A3"},
                    ],
                },
            },
        },
    )


def test_migration_scaffolding_is_removed() -> None:
    template = synthesized_template().to_json()

    assert "DatabaseTarget" not in template["Parameters"]
    assert "ApiDesiredCount" not in template["Parameters"]
    synthesized_template().resource_count_is("AWS::ECS::TaskDefinition", 1)


def test_api_uses_trial_fargate_size() -> None:
    template = synthesized_template()

    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "Cpu": "256",
            "Memory": "512",
        },
    )


def test_replacement_database_is_right_sized_and_protected() -> None:
    template = synthesized_template()

    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "AllocatedStorage": "20",
            "BackupRetentionPeriod": 7,
            "DBInstanceClass": "db.t4g.micro",
            "DeletionProtection": True,
            "Engine": "postgres",
            "EngineVersion": "16",
            "MultiAZ": False,
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "StorageType": "gp3",
        },
    )


def test_database_password_secret_is_retained() -> None:
    template = synthesized_template().to_json()

    target_attachments = [
        resource
        for resource in template["Resources"].values()
        if resource["Type"] == "AWS::SecretsManager::SecretTargetAttachment"
    ]
    assert len(target_attachments) == 0

    database_secret = next(
        resource
        for resource in template["Resources"].values()
        if resource["Type"] == "AWS::SecretsManager::Secret"
        and "GenerateSecretString" in resource["Properties"]
    )
    assert database_secret["DeletionPolicy"] == "Retain"
    assert database_secret["UpdateReplacePolicy"] == "Retain"
