#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
config_file="${DEPLOY_CONFIG:-$project_root/deploy.conf}"
if [[ ! -f "$config_file" ]]; then
    printf 'Missing config: %s\n' "$config_file" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$config_file"
: "${SSH_TARGET:?SSH_TARGET is required in deploy.conf}"
: "${SSH_PASSWORD:?SSH_PASSWORD is required in deploy.conf}"
remote_dir='${HOME}/hackathon'
run_id=$(date +%Y%m%d-%H%M%S)
local_log_dir="$project_root/logs"
local_log="$local_log_dir/start-${run_id}.log"
mkdir -p "$local_log_dir"

if ! command -v sshpass >/dev/null 2>&1; then
    printf 'sshpass is required for password-based SSH without a prompt.\n' >&2
    exit 1
fi

printf 'Starting main.py on %s\n' "$SSH_TARGET"
printf 'Local log: %s\n' "$local_log"
SSHPASS="$SSH_PASSWORD" sshpass -e ssh "$SSH_TARGET" \
    "cd \"$remote_dir\" && exec python3 -u main.py" 2>&1 | tee "$local_log"
