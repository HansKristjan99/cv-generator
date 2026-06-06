#!/usr/bin/env bash
set -euo pipefail
aws_profile="${AWS_PROFILE:-hans-admin}"
aws_region="${AWS_REGION:-eu-north-1}"
frontend_url="${FRONTEND_URL:-https://hireable.vericodehq.com}"
product_id="${PRODUCT_ID:-price_1TatebA9R9bBpPM66m6acvNw}"


script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
infradir="$(cd -- "$script_dir/../infra" && pwd)"

cd "$infradir"

export AWS_PROFILE="$aws_profile"
export AWS_DEFAULT_REGION="$aws_region"
export AWS_REGION="$aws_region"

uv sync --all-packages
uv run --no-sync cdk synth --profile "$aws_profile"
uv run --no-sync cdk diff --profile "$aws_profile" \
  --parameters "FrontendUrl=$frontend_url" \
  --parameters "StripeProPriceId=$product_id"
uv run --no-sync cdk deploy --profile "$aws_profile" \
  --parameters "FrontendUrl=$frontend_url" \
  --parameters "StripeProPriceId=$product_id"
