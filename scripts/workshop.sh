#!/bin/bash

set -e -u -o pipefail

set -x

WORKSHOP_NAME=${WORKSHOP_NAME:-dev}

# Maps "<sdk>:<mount name>" to the host directory it should be backed by.
# The tilde is left unexpanded on purpose; expand_home handles it when used.
declare -A MOUNTS=(
    [flutter:cache]='~/flutter/cache'
    [flutter:dart-tool]='~/.dart-tool'
    [flutter:pub-cache]='~/.pub-cache'
    [uv:cache]='~/.cache/uv'
    [opencode:opencode-config]='~/.config/opencode'
    [opencode:opencode-data]='~/.local/share/opencode'
)

expand_home() {
    printf '%s' "${1/#\~/${HOME}}"
}

# Succeed when the mount already points at the wanted host directory,
# whether workshop reports it with a literal ~ or an expanded path.
mount_is_current() {
    local sdk=${1%%:*} mount=${1#*:} wanted=$2 current
    current=$(yq ".sdks.\"${sdk}\".mounts.\"${mount}\".\"host-source\"" <<<"${INFO}")
    [[ ${current} == "${wanted}" || ${current} == "$(expand_home "${wanted}")" ]]
}

if ! workshop info "${WORKSHOP_NAME}" >&/dev/null; then
    workshop launch "${WORKSHOP_NAME}"
fi
workshop refresh "${WORKSHOP_NAME}" >/dev/null

if ! command -v yq >&/dev/null; then
    sudo snap install yq
fi

# Query the workshop once and check every mount against that snapshot.
INFO=$(workshop info "${WORKSHOP_NAME}")

stale=()
for key in "${!MOUNTS[@]}"; do
    if ! mount_is_current "${key}" "${MOUNTS[${key}]}"; then
        stale+=("${key}")
    fi
done

# The slow stop/start cycle happens once, and only if something is stale.
if ((${#stale[@]} > 0)); then
    workshop stop "${WORKSHOP_NAME}"
    for key in "${stale[@]}"; do
        host_path=$(expand_home "${MOUNTS[${key}]}")
        mkdir --parents "${host_path}"
        workshop remount "${WORKSHOP_NAME}/${key}" "${host_path}"
    done
    workshop start "${WORKSHOP_NAME}"
fi
