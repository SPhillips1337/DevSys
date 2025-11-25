#!/usr/bin/env bash
set -euo pipefail

# run-remote-setup.sh
# Wrapper to upload and run scripts/setup-remote.sh on a remote host using SSH.
# Usage:
#   ./scripts/run-remote-setup.sh <user@host> [--copy] [--script <path>] [--detect-only] [--force]
# Examples:
#   ./scripts/run-remote-setup.sh stephen@192.168.5.69
#   ./scripts/run-remote-setup.sh stephen@host --copy --script ./custom-setup.sh
#   ./scripts/run-remote-setup.sh stephen@host --detect-only

show_help(){
  sed -n '1,120p' "$0" | sed -n '1,40p'
}

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <user@host> [--copy] [--script <path>] [--detect-only] [--force]"
  exit 2
fi

remote="$1"
shift || true
copy_mode=false
custom_script=""
detect_only=false
force=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy)
      copy_mode=true; shift;;
    --script)
      shift; custom_script="$1"; shift;;
    --detect-only)
      detect_only=true; shift;;
    --force)
      force=true; shift;;
    -h|--help)
      show_help; exit 0;;
    *)
      echo "Unknown option: $1"; exit 2;;
  esac
done

local_script_default="$(dirname "$0")/setup-remote.sh"
local_script="${custom_script:-$local_script_default}"

if [ ! -f "$local_script" ]; then
  echo "Local script not found: $local_script"
  exit 1
fi

# Remote OS detection
echo "Detecting remote OS for $remote..."
set +e
os_release=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$remote" 'cat /etc/os-release' 2>/dev/null)
ssh_rc=$?
set -e

if [ $ssh_rc -ne 0 ]; then
  echo "Warning: unable to read /etc/os-release on remote (ssh failed)."
  if [ "$detect_only" = true ]; then
    exit 1
  fi
  if [ "$force" != true ]; then
    echo "Use --force to proceed despite detection failure. Exiting."; exit 1
  fi
else
  # parse ID and VERSION_ID
  remote_id=$(echo "$os_release" | awk -F= '/^ID=/{print $2}' | tr -d '"')
  remote_ver=$(echo "$os_release" | awk -F= '/^VERSION_ID=/{print $2}' | tr -d '"')
  echo "Remote OS detected: ID=$remote_id VERSION_ID=$remote_ver"
  if [ "$detect_only" = true ]; then
    exit 0
  fi
  case "$remote_id" in
    ubuntu|debian|raspbian)
      echo "Detected Debian-derived OS; proceeding with Debian/Ubuntu installer script.";
      ;;
    centos|rhel|fedora|rocky)
      echo "Detected RHEL-derived OS ($remote_id). The default setup script targets Debian/Ubuntu."
      if [ "$force" = true ]; then
        echo "--force given: proceeding anyway."
      else
        echo "Either provide a custom script via --script or re-run with --force to proceed anyway."; exit 1
      fi
      ;;
    *)
      echo "Unknown remote OS: $remote_id. Provide a custom setup script with --script or rerun with --force.";
      if [ "$force" != true ]; then exit 1; fi
      ;;
  esac
fi

# If we've reached here, either detection succeeded and OS is supported, or user forced/allowed.
if [ "$copy_mode" = true ]; then
  echo "Copying $local_script to $remote:~/setup-remote.sh..."
  scp "$local_script" "$remote:~/setup-remote.sh"
  echo "Running remote script with sudo..."
  ssh "$remote" 'sudo bash ~/setup-remote.sh'
  echo "Remote setup complete. You may remove ~/setup-remote.sh on the remote host if desired."
else
  echo "Streaming and executing $local_script on $remote (you will be prompted for password if needed)..."
  cat "$local_script" | ssh "$remote" 'sudo bash -s'
  echo "Remote setup complete."
fi

exit 0
