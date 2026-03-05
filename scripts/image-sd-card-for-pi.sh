#!/usr/bin/env bash
# image-sd-card-for-pi.sh
#
# Write a Ubuntu Noble (24.04 LTS) preinstalled server image to an SD card
# for a Raspberry Pi 5 (or any Pi 3/4/5/CM4/Zero 2 W), then optionally
# inject cloud-init seed files into the system-boot partition.
#
# The image used is:
#   ubuntu-24.04-preinstalled-server-arm64+raspi.img.xz
#
# Ubuntu publishes a single "generic" arm64+raspi image that supports the
# Pi 3, 4, 5, CM4 and Zero 2 W via the same kernel and firmware.  The Pi 5
# is fully supported from Ubuntu 23.10 onwards; Noble (24.04 LTS) is the
# current LTS release with full Pi 5 support.
#
# The download URL uses the stable /releases/noble/release/ redirect, which
# always resolves to the latest 24.04.x point release without you having to
# update this script when Canonical publishes a new point release (e.g.
# 24.04.1 → 24.04.2 → …).
#
# Usage:
#   sudo is NOT required to run this script; individual commands that need
#   root call sudo internally.
#
#   ./image-sd-card-for-pi.sh [OPTIONS] [DEVICE]
#
#   DEVICE  Block device to write to.  Defaults to /dev/mmcblk0.
#           Examples: /dev/mmcblk0  /dev/sdb
#
# Options:
#   --cloud-init              Inject cloud-init seed files into the
#                             system-boot partition after writing the image.
#                             Reads user-data from scripts/cloud-init/user-data.j2
#                             and network-config from scripts/cloud-init/network-config.yaml.
#
#   --var KEY=VALUE           Set a template variable for user-data.j2.
#                             May be repeated.  Example:
#                               --var pumaguard_passwd_hash='$6$...'
#                               --var hostname=mypi
#                               --var timezone=Europe/Berlin
#                               --var ssh_authorized_key='ssh-ed25519 AAAA...'
#
#   --vars-file FILE          Path to a shell-style KEY=VALUE file (one per
#                             line, blank lines and # comments ignored).
#                             Variables set here are overridden by --var.
#
# Required template variable:
#   pumaguard_passwd_hash     SHA-512 shadow password hash for the pumaguard
#                             user.  Generate one with:
#                               openssl passwd -6
#
# Prerequisites (all available via apt on Ubuntu/Debian):
#   wget, xz-utils, jq, udisks2, util-linux (lsblk / partprobe), python3
#
# WARNING: This script ERASES the target device completely.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SDCARD=""
DO_CLOUD_INIT=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD_INIT_DIR="${SCRIPT_DIR}/cloud-init"
USER_DATA_TEMPLATE="${CLOUD_INIT_DIR}/user-data.j2"
NETWORK_CONFIG="${CLOUD_INIT_DIR}/network-config.yaml"

BASE_URL="https://cdimage.ubuntu.com/releases/noble/release"
IMAGE_XZ="ubuntu-24.04-preinstalled-server-arm64+raspi.img.xz"
IMAGE_RAW="${IMAGE_XZ%.xz}"
SUMS_FILE="SHA256SUMS"

# Associative array for template variables (requires bash 4+)
declare -A TEMPLATE_VARS=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

usage() {
    sed -n '/^# Usage:/,/^[^#]/{ /^[^#]/d; s/^# \{0,3\}//; p }' "$0"
    exit 0
}

require_cmd() {
    for cmd in "$@"; do
        command -v "${cmd}" >/dev/null 2>&1 || \
            die "'${cmd}' not found. Install it and re-run (e.g. sudo apt install ${cmd})."
    done
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cloud-init)
            DO_CLOUD_INIT=true
            shift
            ;;
        --var)
            [[ $# -ge 2 ]] || die "--var requires an argument (KEY=VALUE)"
            key="${2%%=*}"
            value="${2#*=}"
            [[ -n "${key}" ]] || die "--var argument must be in KEY=VALUE form"
            TEMPLATE_VARS["${key}"]="${value}"
            shift 2
            ;;
        --vars-file)
            [[ $# -ge 2 ]] || die "--vars-file requires a path argument"
            vars_file="$2"
            [[ -f "${vars_file}" ]] || die "vars file not found: ${vars_file}"
            while IFS= read -r line || [[ -n "${line}" ]]; do
                # Skip blank lines and comments
                [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
                key="${line%%=*}"
                value="${line#*=}"
                # Don't overwrite variables already set via --var
                if [[ -z "${TEMPLATE_VARS["${key}"]+set}" ]]; then
                    TEMPLATE_VARS["${key}"]="${value}"
                fi
            done < "${vars_file}"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        --*)
            die "Unknown option: $1"
            ;;
        *)
            # Positional: device
            [[ -z "${SDCARD}" ]] || die "Unexpected extra argument: $1"
            SDCARD="$1"
            shift
            ;;
    esac
done

SDCARD="${SDCARD:-/dev/mmcblk0}"

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

require_cmd wget xz lsblk jq udisksctl partprobe udevadm sha256sum

if "${DO_CLOUD_INIT}"; then
    require_cmd python3
    [[ -f "${USER_DATA_TEMPLATE}" ]] || \
        die "user-data template not found: ${USER_DATA_TEMPLATE}"
    [[ -f "${NETWORK_CONFIG}" ]] || \
        die "network-config not found: ${NETWORK_CONFIG}"
    [[ -n "${TEMPLATE_VARS["pumaguard_passwd_hash"]+set}" ]] || \
        die "pumaguard_passwd_hash is required when using --cloud-init.
Generate one with:  openssl passwd -6
Then pass it via:   --var pumaguard_passwd_hash='\$6\$...'"
fi

[[ -b "${SDCARD}" ]] || \
    die "${SDCARD} is not a block device. Check the device name and try again."

# Refuse to write to what looks like the system disk (mounted at /).
ROOT_DEVICE="$(lsblk --noheadings --output PKNAME \
    "$(findmnt --noheadings --output SOURCE /)" 2>/dev/null || true)"
if [[ -n "${ROOT_DEVICE}" && "/dev/${ROOT_DEVICE}" == "${SDCARD}" ]]; then
    die "${SDCARD} appears to be the system (root) disk. Aborting for safety."
fi

info "Target device : ${SDCARD}"
info "Image         : ${IMAGE_XZ}"
"${DO_CLOUD_INIT}" && info "Cloud-init    : enabled"
info ""
warn "ALL DATA ON ${SDCARD} WILL BE DESTROYED."
read -r -p "Type YES to continue: " answer
[[ "${answer}" == "YES" ]] || die "Aborted by user."

# ---------------------------------------------------------------------------
# Unmount any partitions that are currently mounted
# ---------------------------------------------------------------------------

info "Unmounting any mounted partitions on ${SDCARD} ..."
readarray -t MOUNTPOINTS < <(
    lsblk --json "${SDCARD}" 2>/dev/null \
        | jq --raw-output '.. | .mountpoints? // empty | .[]' \
        | grep -v '^null$' \
    || true
)

for mp in "${MOUNTPOINTS[@]+"${MOUNTPOINTS[@]}"}"; do
    info "  Unmounting ${mp}"
    sudo umount "${mp}"
done

# ---------------------------------------------------------------------------
# Download image + checksum file
# ---------------------------------------------------------------------------

info "Downloading SHA256SUMS ..."
wget --timestamping --continue "${BASE_URL}/${SUMS_FILE}"

info "Downloading ${IMAGE_XZ} (this may take a while — ~1.2 GB) ..."
wget --timestamping --continue "${BASE_URL}/${IMAGE_XZ}"

# ---------------------------------------------------------------------------
# Verify checksum of the compressed image
# ---------------------------------------------------------------------------

info "Verifying SHA256 checksum of ${IMAGE_XZ} ..."

EXPECTED_LINE="$(grep "${IMAGE_XZ}" "${SUMS_FILE}")" \
    || die "Could not find ${IMAGE_XZ} in ${SUMS_FILE}.
The checksum file may be for a different point release.
Delete ${SUMS_FILE} and retry."

echo "${EXPECTED_LINE}" | sha256sum --check --status \
    || die "SHA256 checksum mismatch for ${IMAGE_XZ}!
The file may be corrupt or tampered with. Delete it and retry."

info "Checksum OK."

# ---------------------------------------------------------------------------
# Decompress (keep the .xz so re-runs don't re-download)
# ---------------------------------------------------------------------------

if [[ ! -f "${IMAGE_RAW}" ]]; then
    info "Decompressing ${IMAGE_XZ} -> ${IMAGE_RAW} ..."
    xz --keep --decompress --force "${IMAGE_XZ}"
else
    info "${IMAGE_RAW} already exists, skipping decompression."
fi

# ---------------------------------------------------------------------------
# Write image to SD card
# ---------------------------------------------------------------------------

info "Writing ${IMAGE_RAW} to ${SDCARD} ..."
info "(This will take several minutes — watch the progress indicator below)"
sudo dd \
    if="${IMAGE_RAW}" \
    of="${SDCARD}" \
    bs=4M \
    status=progress

info "Flushing write cache ..."
sudo sync

# ---------------------------------------------------------------------------
# Re-read the partition table and mount the new partitions
# ---------------------------------------------------------------------------

info "Re-reading partition table ..."
sudo udevadm settle
sudo partprobe "${SDCARD}"
sudo udevadm trigger --sysname-match="$(basename "${SDCARD}")" --action=change
sudo udevadm settle

info "Mounting new partitions ..."
readarray -t PARTITIONS < <(
    lsblk --json "${SDCARD}" 2>/dev/null \
        | jq --raw-output '.blockdevices[].children[]?.name // empty' \
    || true
)

for part in "${PARTITIONS[@]+"${PARTITIONS[@]}"}"; do
    for attempt in $(seq 1 5); do
        if udisksctl mount --block-device "/dev/${part}" 2>/dev/null; then
            break
        fi
        warn "  Mount attempt ${attempt}/5 for /dev/${part} failed, retrying ..."
        sleep 1
    done
done

# ---------------------------------------------------------------------------
# cloud-init injection
# ---------------------------------------------------------------------------

if "${DO_CLOUD_INIT}"; then

    # The Ubuntu raspi image names its FAT boot partition "system-boot".
    # udisksctl mounts it under /media/$USER/system-boot (or /run/media/...).
    SYSTEM_BOOT_MOUNT="$(
        lsblk --json "${SDCARD}" 2>/dev/null \
            | jq --raw-output '
                .. | objects
                   | select(.label? == "system-boot")
                   | .mountpoints[]?
                   | select(. != null)
              ' \
            | head -1
    )"

    [[ -n "${SYSTEM_BOOT_MOUNT}" ]] || \
        die "Could not find a mounted system-boot partition on ${SDCARD}.
Ensure the partition was mounted successfully before retrying."

    info "system-boot partition mounted at: ${SYSTEM_BOOT_MOUNT}"

    # Build a Python dict literal from TEMPLATE_VARS so we can pass it to
    # the inline Jinja2 renderer without touching the filesystem.
    # Values are single-quote-escaped: any single quote in the value becomes '\''
    PYTHON_DICT="{"
    first=true
    for key in "${!TEMPLATE_VARS[@]}"; do
        value="${TEMPLATE_VARS["${key}"]}"
        # Escape single quotes for embedding in a Python single-quoted string
        escaped_value="${value//\'/\'\\\'\'}"
        "${first}" || PYTHON_DICT+=", "
        PYTHON_DICT+="'${key}': '${escaped_value}'"
        first=false
    done
    PYTHON_DICT+="}"

    # Render user-data.j2 using Python's built-in string.Template would not
    # handle Jinja2 syntax, so we use the jinja2 package if available, falling
    # back to a simple sed-based substitution for the common scalar variables.
    info "Rendering user-data from template ..."

    if python3 -c "import jinja2" 2>/dev/null; then
        RENDERED_USER_DATA="$(python3 - <<PYEOF
import sys
import jinja2

template_path = '${USER_DATA_TEMPLATE}'
variables = ${PYTHON_DICT}

with open(template_path, 'r') as f:
    source = f.read()

# Use jinja2 with undefined=Undefined so missing optional vars render as ''.
env = jinja2.Environment(
    keep_trailing_newline=True,
    undefined=jinja2.Undefined,
)
template = env.from_string(source)
print(template.render(**variables), end='')
PYEOF
)"
    else
        warn "Python jinja2 package not found; falling back to sed-based rendering."
        warn "Install it for full template support:  pip3 install jinja2"

        # Minimal sed rendering: replace {{ KEY }} and {{ KEY | default('...') }}
        # This handles all scalar variables used in user-data.j2.
        tmp_render="$(mktemp)"
        cp "${USER_DATA_TEMPLATE}" "${tmp_render}"

        for key in "${!TEMPLATE_VARS[@]}"; do
            value="${TEMPLATE_VARS["${key}"]}"
            # Escape sed replacement delimiters
            escaped_value="$(printf '%s\n' "${value}" | sed 's/[&/\]/\\&/g')"
            # Replace {{ key }} and {{ key | default('...') }}
            sed -i \
                -e "s|{{ ${key} }}|${escaped_value}|g" \
                -e "s|{{ ${key} | default('[^']*') }}|${escaped_value}|g" \
                "${tmp_render}"
        done

        # Replace any remaining {{ VAR | default('FALLBACK') }} with FALLBACK
        sed -i -E "s|\{\{ [a-zA-Z_]+ \| default\('([^']*)'\) \}\}|\1|g" "${tmp_render}"

        RENDERED_USER_DATA="$(cat "${tmp_render}")"
        rm -f "${tmp_render}"
    fi

    # Write user-data (needs root because system-boot may be root-owned after dd)
    info "Writing user-data to ${SYSTEM_BOOT_MOUNT}/user-data ..."
    echo "${RENDERED_USER_DATA}" | sudo tee "${SYSTEM_BOOT_MOUNT}/user-data" > /dev/null

    # Write network-config (static file, no rendering needed)
    info "Writing network-config to ${SYSTEM_BOOT_MOUNT}/network-config ..."
    sudo cp "${NETWORK_CONFIG}" "${SYSTEM_BOOT_MOUNT}/network-config"

    # Flush writes to the FAT partition
    sudo sync

    info "cloud-init files written successfully."
    info ""
    info "  user-data   : ${SYSTEM_BOOT_MOUNT}/user-data"
    info "  network-config : ${SYSTEM_BOOT_MOUNT}/network-config"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

info ""
info "Done!  Partition layout:"
lsblk "${SDCARD}"
info ""
info "Next steps:"
info "  1. Eject the SD card safely:"
info "       udisksctl power-off --block-device ${SDCARD}"
info "  2. Insert it into the Pi and power on."
if "${DO_CLOUD_INIT}"; then
    info "  3. Wait for cloud-init to finish (~2 min on first boot)."
    info "     Login: pumaguard / <the password you hashed>"
    info "     The device will be reachable as raspberrypi.local once"
    info "     avahi-daemon starts."
else
    info "  3. Default login: ubuntu / ubuntu  (you will be prompted to change"
    info "     the password on first login)."
fi
info "  4. Run the Ansible playbook:"
info "       ansible-playbook scripts/configure-device.yaml"
