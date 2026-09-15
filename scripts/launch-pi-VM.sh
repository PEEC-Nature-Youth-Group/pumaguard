#!/bin/bash

set -e -u -o pipefail

declare force=0
declare vm_name=${vm_name:=pumaguard}
declare model="zero"
declare -A resource_limits=(
    ["0"]="512M 64G 1"
    ["3"]="1G   64G 1"
    ["4"]="1G   64G 1"
    ["5"]="2G   64G 1"
)

while (( $# > 0 )); do
    case $1 in
        -h|--help)
            cat <<EOF
Script to launch a Raspberry Pi Zero W virtual machine.

Options:

--name VM_NAME      The name of the VM (required)
--force             Delete existing VM
--list-models       List known Raspberry Pi models
--model MODEL       Use MODEL (default '${model}') resource limits
EOF
            exit
            ;;
        --name)
            shift
            vm_name="$1"
            ;;
        --force)
            force=$(( (force + 1)%2 ))
            ;;
        --list-models)
            echo "Known Raspberry Pi models"
            for model in "${!resource_limits[@]}"; do
                echo "  ${model}"
            done
            exit 0
            ;;
        --model)
            shift
            model=$1
            if [[ ! -v resource_limits[${model}] ]]; then
                echo "unknown model"
                exit 1
            fi
            ;;
    esac
    shift
done

if [[ -z ${vm_name} ]]; then
    echo "missing VM name"
    exit 1
fi

read -a temp -r <<< ${resource_limits[${model}]}
memory=${temp[0]}
disk=${temp[1]}
vcpus=${temp[2]}

if (( force == 1 )); then
    multipass delete --purge "${vm_name}"
fi
echo "Starting Pi-${model} VM ${vm_name}"
multipass launch core24 \
    --memory ${memory} \
    --disk ${disk} \
    --cpus ${vcpus} \
    --name "${vm_name}"
