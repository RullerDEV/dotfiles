#!/usr/bin/env bash
set -euo pipefail

FLAG=/tmp/gamemode
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
M1_M4_MACRO="$DIR/m1_m4_macro.sh"

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -a "gamemode" "gamemode" "$1" 2>/dev/null || true
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

macro_start() {
    if [ -f "$M1_M4_MACRO" ]; then
        bash "$M1_M4_MACRO" start >/dev/null 2>&1 || true
    fi
}

macro_stop() {
    if [ -f "$M1_M4_MACRO" ]; then
        bash "$M1_M4_MACRO" stop >/dev/null 2>&1 || true
    fi
}

restart_waybar() {
    if command -v waybar >/dev/null 2>&1 && ! pgrep -x waybar >/dev/null 2>&1; then
        if command -v hyprctl >/dev/null 2>&1; then
            hyprctl dispatch exec waybar >/dev/null 2>&1 || nohup waybar >/dev/null 2>&1 &
        else
            nohup waybar >/dev/null 2>&1 &
        fi
    fi
}

enable_gamemode() {
    touch "$FLAG"
    pkill -x waybar 2>/dev/null || true
    dnd_on
    macro_start

    hyprctl --batch "\
        keyword animations:enabled false ; \
        keyword decoration:blur:enabled false ; \
        keyword decoration:shadow:enabled false ; \
        keyword decoration:rounding 0 ; \
        keyword decoration:active_opacity 1.0 ; \
        keyword decoration:inactive_opacity 1.0 ; \
        keyword general:gaps_in 0 ; \
        keyword general:gaps_out 0 ; \
        keyword general:border_size 0 ; \
        keyword general:allow_tearing true ; \
        keyword misc:animate_manual_resizes false ; \
        keyword misc:animate_mouse_windowdragging false ; \
        keyword debug:vfr false ; \
        keyword cursor:no_break_fs_vrr 1 ; \
        keyword cursor:no_hardware_cursors false ; \
        keyword render:direct_scanout 1" >/dev/null 2>&1 || true

    notify "on: minimal profile, DND, no bar, no blur"
}

disable_gamemode() {
    rm -f "$FLAG"
    macro_stop
    hyprctl reload >/dev/null 2>&1 || true
    restart_waybar
    dnd_off
    notify "off: clean profile restored"
}

status() {
    if [ -f "$FLAG" ]; then
        echo "on"
    else
        echo "off"
    fi
}

waybar() {
    if [ -f "$FLAG" ]; then
        printf '{"text":"󰊴","tooltip":"gamemode on","class":"on"}\n'
    else
        printf '{"text":"󰊴","tooltip":"gamemode off","class":"off"}\n'
    fi
}

case "${1:-toggle}" in
    on|enable)
        enable_gamemode
        ;;
    off|disable)
        disable_gamemode
        ;;
    toggle)
        if [ -f "$FLAG" ]; then
            disable_gamemode
        else
            enable_gamemode
        fi
        ;;
    status)
        status
        ;;
    waybar)
        waybar
        ;;
    *)
        echo "usage: $0 [toggle|on|off|status|waybar]" >&2
        exit 2
        ;;
esac
