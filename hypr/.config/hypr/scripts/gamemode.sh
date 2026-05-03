#!/usr/bin/env bash
set -euo pipefail

FLAG=/tmp/gamemode

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "gamemode" "$1"
    fi
}

dnd_on() {
    if command -v swaync-client >/dev/null 2>&1; then
        swaync-client -dn >/dev/null 2>&1 || true
    elif command -v dunstctl >/dev/null 2>&1; then
        dunstctl set-paused true >/dev/null 2>&1 || true
    fi
}

dnd_off() {
    if command -v swaync-client >/dev/null 2>&1; then
        swaync-client -df >/dev/null 2>&1 || true
    elif command -v dunstctl >/dev/null 2>&1; then
        dunstctl set-paused false >/dev/null 2>&1 || true
    fi
}

enable_gamemode() {
    pkill -x waybar 2>/dev/null || true
    dnd_on

    hyprctl --batch "\
        keyword animations:enabled false ; \
        keyword decoration:blur:enabled false ; \
        keyword decoration:shadow:enabled false ; \
        keyword decoration:active_opacity 1.0 ; \
        keyword decoration:inactive_opacity 1.0 ; \
        keyword general:gaps_in 0 ; \
        keyword general:gaps_out 0 ; \
        keyword general:border_size 0 ; \
        keyword misc:vfr false" >/dev/null 2>&1 || true

    notify "ativado"
}

disable_gamemode() {
    hyprctl reload >/dev/null 2>&1 || true
    nohup waybar >/dev/null 2>&1 &
    dnd_off
    notify "desativado"
}

case "${1:-toggle}" in
    on|enable)
        touch "$FLAG"
        enable_gamemode
        ;;
    off|disable)
        rm -f "$FLAG"
        disable_gamemode
        ;;
    toggle)
        if [ -f "$FLAG" ]; then
            rm -f "$FLAG"
            disable_gamemode
        else
            touch "$FLAG"
            enable_gamemode
        fi
        ;;
    *)
        echo "usage: $0 [toggle|on|off]" >&2
        exit 2
        ;;
esac
