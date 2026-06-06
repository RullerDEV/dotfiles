#!/usr/bin/env bash
set -euo pipefail

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}"
STATE_FILE="$CACHE_DIR/theme"
mkdir -p "$CACHE_DIR"

current="$(cat "$STATE_FILE" 2>/dev/null || echo light)"
mode="${1:-toggle}"

case "$mode" in
    toggle)
        if [ "$current" = "dark" ]; then
            next="light"
        else
            next="dark"
        fi
        ;;
    light|dark)
        next="$mode"
        ;;
    *)
        echo "usage: $0 [toggle|light|dark]" >&2
        exit 2
        ;;
esac

echo -n "$next" > "$STATE_FILE"

link() {
    local src="$1" dst="$2"
    [ -e "$src" ] || return 0
    mkdir -p "$(dirname "$dst")"
    ln -sfn "$src" "$dst"
}

link "$HOME/.config/hypr/themes/${next}.conf"        "$HOME/.config/hypr/themes/current.conf"
link "$HOME/.config/waybar/themes/${next}.css"       "$HOME/.config/waybar/themes/current.css"
link "$HOME/.config/kitty/themes/${next}.conf"       "$HOME/.config/kitty/themes/current.conf"
link "$HOME/.config/rofi/themes/mono-${next}.rasi"   "$HOME/.config/rofi/themes/current.rasi"
link "$HOME/.config/yazi/themes/mono-${next}.toml"   "$HOME/.config/yazi/themes/current.toml"
link "$HOME/.config/swaync/themes/${next}.css"       "$HOME/.config/swaync/themes/current.css"
link "$HOME/.config/wlogout/themes/${next}.css"      "$HOME/.config/wlogout/themes/current.css"

if command -v hyprctl >/dev/null 2>&1; then
    hyprctl reload >/dev/null 2>&1 || true
fi

if pgrep -x waybar >/dev/null 2>&1; then
    pkill -SIGUSR2 waybar >/dev/null 2>&1 || true
fi

if command -v kitty >/dev/null 2>&1; then
    for sock in /tmp/kitty*; do
        [ -S "$sock" ] || continue
        kitty @ --to "unix:$sock" set-colors --all "$HOME/.config/kitty/themes/current.conf" >/dev/null 2>&1 || true
    done
fi

if pgrep -x swaync >/dev/null 2>&1; then
    swaync-client -rs >/dev/null 2>&1 || true
fi

if pgrep -x yazi >/dev/null 2>&1; then
    pkill -USR1 yazi 2>/dev/null || true
fi

if command -v notify-send >/dev/null 2>&1; then
    notify-send -a "settings" "theme: $next" 2>/dev/null || true
fi
