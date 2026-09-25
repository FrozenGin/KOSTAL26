#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: %s\n' "$0"
    printf '\nCreate deploy.conf from deploy.conf.example first.\n'
}

if [[ $# -ne 0 ]]; then
    usage >&2
    exit 2
fi

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
config_file="${DEPLOY_CONFIG:-$project_root/deploy.conf}"
if [[ ! -f "$config_file" ]]; then
    printf 'Missing config: %s\n' "$config_file" >&2
    printf 'Copy deploy.conf.example to deploy.conf and edit it.\n' >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$config_file"
: "${SSH_TARGET:?SSH_TARGET is required in deploy.conf}"
: "${SSH_PASSWORD:?SSH_PASSWORD is required in deploy.conf}"
WIFI_CHANGE=${WIFI_CHANGE:-false}
WIFI_SSID=${WIFI_SSID:-}
WIFI_PASSWORD=${WIFI_PASSWORD:-}
remote_dir='${HOME}/hackathon'
run_id=$(date +%Y%m%d-%H%M%S)
local_log_dir="$project_root/logs"
local_log="$local_log_dir/run-${run_id}.log"
mkdir -p "$local_log_dir"

if ! command -v sshpass >/dev/null 2>&1; then
    printf 'sshpass is required for password-based SSH without a prompt.\n' >&2
    exit 1
fi

ssh_robot() {
    SSHPASS="$SSH_PASSWORD" sshpass -e ssh "$SSH_TARGET" "$@"
}

if [[ "$WIFI_CHANGE" == "true" ]]; then
    if [[ -z "$WIFI_SSID" || -z "$WIFI_PASSWORD" ]]; then
        printf 'WIFI_SSID and WIFI_PASSWORD are required when WIFI_CHANGE=true.\n' >&2
        exit 1
    fi
    printf 'Changing local PC Wi-Fi to %s\n' "$WIFI_SSID"
    nmcli device wifi connect "$WIFI_SSID" password "$WIFI_PASSWORD"
    sleep 5
fi

printf 'Copying project to %s:%s\n' "$SSH_TARGET" "$remote_dir"
tar \
    --transform='s,^Version2/app.py$,app.py,' \
    --transform='s,^Version2/config.py$,config.py,' \
    --transform='s,^Version2/models.py$,models.py,' \
    --transform='s,^Version2/state_machine.py$,state_machine.py,' \
    --transform='s,^Version2/control/line_controller.py$,line_controller.py,' \
    --transform='s,^Version2/perception/line_analysis.py$,line_analysis.py,' \
    --transform='s,^Version2/perception/qr_commands.py$,qr_commands.py,' \
    --transform='s,^Version2/hardware/picar.py$,picar_adapter.py,' \
    --transform='s,^Version2/hardware/qr_camera.py$,qr_camera.py,' \
    -C "$project_root" -cf - \
    main.py \
    Version2/app.py \
    Version2/config.py \
    Version2/models.py \
    Version2/state_machine.py \
    Version2/control/line_controller.py \
    Version2/perception/line_analysis.py \
    Version2/perception/qr_commands.py \
    Version2/hardware/picar.py \
    Version2/hardware/qr_camera.py |
    ssh_robot "mkdir -p \"$remote_dir\" && tar -xf - -C \"$remote_dir\""

printf 'Starting V2 on %s\n' "$SSH_TARGET"
printf 'Starting through start.sh\n'
"$project_root/start.sh"
