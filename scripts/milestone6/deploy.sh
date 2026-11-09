#!/usr/bin/env bash
set -euo pipefail

candidate_image=${1:?Image digest required}
candidate_commit=${2:?Commit SHA required}
url=https://metroai.136.81.119.160.sslip.io
kube=(kubectl --namespace metroai)
deployment=deployment/metroai
image_path='{.spec.template.spec.containers[?(@.name=="app")].image}'

public_commit() {
    curl --fail --silent --show-error --max-time 5 "$url/api/version" |
        jq -er '.commit'
}

verify_https() {
    local expected_commit=$1
    local attempt
    for attempt in {1..15}; do
        if curl --fail --silent --show-error --max-time 5 "$url/api/health/ready" |
            jq -e '.status == "ready"' >/dev/null; then
            if [[ -z $expected_commit || $(public_commit) == "$expected_commit" ]]; then
                return 0
            fi
        fi
        sleep 4
    done
    return 1
}

"${kube[@]}" rollout status "$deployment" --timeout=45s
verify_https ''
previous_revision=$("${kube[@]}" get "$deployment" -o 'jsonpath={.metadata.annotations.deployment\.kubernetes\.io/revision}')
previous_image=$("${kube[@]}" get "$deployment" -o "jsonpath=$image_path")
# The Milestone 5 image predates /api/version. Its digest is still verified.
previous_commit=$(public_commit 2>/dev/null || true)
printf 'Healthy baseline: revision %s, image %s, commit %s\n' "$previous_revision" "$previous_image" "${previous_commit:-pre-Milestone-6}"

fail_readiness=0
if [[ -f deploy/milestone6-fail-readiness ]]; then
    fail_readiness=1
fi
patch=$(jq -cn --arg image "$candidate_image" --arg commit "$candidate_commit" --arg fail "$fail_readiness" '{
  spec: {template: {spec: {containers: [{name: "app", image: $image, env: [
    {name: "METROAI_BUILD_SHA", value: $commit},
    {name: "METROAI_FAIL_READINESS", value: $fail}
  ]}]}}}
}')

if "${kube[@]}" patch "$deployment" --type strategic --patch "$patch" &&
    "${kube[@]}" rollout status "$deployment" --timeout=150s &&
    verify_https "$candidate_commit"; then
    printf 'Deployment verified over HTTPS. Serving commit %s\n' "$candidate_commit"
    exit 0
fi

printf 'Candidate failed. Rolling back to revision %s\n' "$previous_revision"
"${kube[@]}" rollout undo "$deployment" --to-revision="$previous_revision"
"${kube[@]}" rollout status "$deployment" --timeout=240s
restored_image=$("${kube[@]}" get "$deployment" -o "jsonpath=$image_path")
if [[ $restored_image != "$previous_image" ]] || ! verify_https "$previous_commit"; then
    printf 'Rollback verification failed. Current image: %s\n' "$restored_image" >&2
    exit 1
fi
printf 'Rollback verified over HTTPS. Serving commit %s, image %s\n' "${previous_commit:-pre-Milestone-6}" "$restored_image"
exit 1
