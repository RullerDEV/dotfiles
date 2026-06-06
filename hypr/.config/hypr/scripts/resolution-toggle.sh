#!/usr/bin/env bash
set -euo pipefail

MONITOR="DP-1"
POS="1920x0"
SCALE="1"

NATIVE_RES="1920x1080@180"
ALT_RES="1440x1080@180"

FLAG=/tmp/dp1-alt-resolution

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "resolução" "$1"
    fi
}

apply() {
    local res="$1"
    hyprctl keyword monitor "${MONITOR},${res},${POS},${SCALE}" >/dev/null 2>&1 || {
        notify "falha ao aplicar ${res}"
        exit 1
    }
}

set_alt() {
    apply "$ALT_RES"
    touch "$FLAG"
    notify "${MONITOR} → ${ALT_RES}"
}

set_native() {
    apply "$NATIVE_RES"
    rm -f "$FLAG"
    notify "${MONITOR} → ${NATIVE_RES}"
}

case "${1:-toggle}" in
    alt|on)
        set_alt
        ;;
    native|off)
        set_native
        ;;
    toggle)
        if [ -f "$FLAG" ]; then
            set_native
        else
            set_alt
        fi
        ;;
    *)
        echo "usage: $0 [toggle|alt|native]" >&2
        exit 2
        ;;
esac
