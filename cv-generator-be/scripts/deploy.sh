#!/usr/bin/env bash
set -euo pipefail

aws_profile="hans-admin"
aws_region="eu-north-1"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
infradir="$(cd -- "$script_dir/../infra" && pwd)"

cd "$infradir"

export AWS_PROFILE="$aws_profile"
export AWS_DEFAULT_REGION="$aws_region"
export AWS_REGION="$aws_region"

uv sync
uv run cdk synth --profile "$aws_profile"
uv run cdk diff --profile "$aws_profile"
uv run cdk deploy --profile "$aws_profile"