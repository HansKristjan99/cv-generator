import aws_cdk as cdk

from infra.infra_stack import CvGeneratorBeStack

app = cdk.App()

CvGeneratorBeStack(
    app,
    "CvGeneratorBeStack",
    env=cdk.Environment(
        account="643681787037",
        region="eu-north-1",
    ),
)

app.synth()
