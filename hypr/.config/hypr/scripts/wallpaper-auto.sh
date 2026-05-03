#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${WALLPAPER_INTERVAL:-900}"
SCRIPT="$HOME/.config/hypr/scripts/wallpaper.sh"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/wallpaper-auto.lock"

if [ ! -x "$SCRIPT" ]; then
    echo "wallpaper script not found: $SCRIPT" >&2
    exit 1
fi

mkdir -p "$(dirname "$LOCK")"

exec 9>"$LOCK"
if ! flock -n 9; then
    exit 0
fi

while true; do
    sleep "$INTERVAL"
    "$SCRIPT" random >/dev/null 2>&1 || true
done
