import os
import aws_cdk as cdk

from infra.infra_stack import CvGeneratorBeStack

app = cdk.App()

CvGeneratorBeStack(
    app,
    "CvGeneratorBeStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()