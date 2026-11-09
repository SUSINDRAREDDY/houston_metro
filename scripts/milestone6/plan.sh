#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
terraform_bin=${TERRAFORM_BIN:-terraform}
if ! command -v "$terraform_bin" >/dev/null; then
    terraform_bin="$HOME/.local/share/metroai-milestone6/bin/terraform"
fi
if [[ ! -s $repo_dir/terraform/terraform.tfstate ]]; then
    printf 'Use the Milestone 6 checkout containing the private Terraform state.\n' >&2
    exit 1
fi
# Supply a fresh short-lived credential without echoing it in the terminal.
export GOOGLE_OAUTH_ACCESS_TOKEN
GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
exec "$terraform_bin" -chdir="$repo_dir/terraform" plan -refresh=true -detailed-exitcode -input=false -no-color
