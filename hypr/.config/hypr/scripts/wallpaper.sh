#!/usr/bin/env bash
set -euo pipefail

WALL_DIR="${WALL_DIR:-$HOME/Pictures/Wallpapers}"
STATE="${XDG_CACHE_HOME:-$HOME/.cache}/wallpaper"
TRANS_TYPE="${TRANS_TYPE:-grow}"
TRANS_DUR="${TRANS_DUR:-1.2}"

mkdir -p "$WALL_DIR" "$(dirname "$STATE")"

if ! command -v swww >/dev/null 2>&1; then
    echo "swww not installed" >&2
    exit 1
fi

if ! pgrep -x swww-daemon >/dev/null 2>&1; then
    swww-daemon >/dev/null 2>&1 &
    sleep 0.4
fi

mapfile -t walls < <(find "$WALL_DIR" -maxdepth 2 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) | sort)

set_wall() {
    local img="$1"
    swww img "$img" --transition-type "$TRANS_TYPE" --transition-duration "$TRANS_DUR" --transition-fps 60
    echo -n "$img" > "$STATE"
}

cmd="${1:-init}"
case "$cmd" in
    init)
        if [ "${#walls[@]}" -eq 0 ]; then
            exit 0
        fi
        if [ -s "$STATE" ] && [ -f "$(cat "$STATE")" ]; then
            set_wall "$(cat "$STATE")"
        else
            set_wall "${walls[0]}"
        fi
        ;;
    next)
        if [ "${#walls[@]}" -eq 0 ]; then
            exit 0
        fi
        cur="$(cat "$STATE" 2>/dev/null || echo "")"
        idx=0
        for i in "${!walls[@]}"; do
            if [ "${walls[$i]}" = "$cur" ]; then
                idx=$(( (i + 1) % ${#walls[@]} ))
                break
            fi
        done
        set_wall "${walls[$idx]}"
        ;;
    prev)
        if [ "${#walls[@]}" -eq 0 ]; then
            exit 0
        fi
        cur="$(cat "$STATE" 2>/dev/null || echo "")"
        idx=0
        for i in "${!walls[@]}"; do
            if [ "${walls[$i]}" = "$cur" ]; then
                idx=$(( (i - 1 + ${#walls[@]}) % ${#walls[@]} ))
                break
            fi
        done
        set_wall "${walls[$idx]}"
        ;;
    random)
        if [ "${#walls[@]}" -eq 0 ]; then
            exit 0
        fi
        idx=$(( RANDOM % ${#walls[@]} ))
        set_wall "${walls[$idx]}"
        ;;
    set)
        img="${2:-}"
        if [ -z "$img" ] || [ ! -f "$img" ]; then
            echo "usage: $0 set <image>" >&2
            exit 2
        fi
        set_wall "$img"
        ;;
    *)
        echo "usage: $0 [init|next|prev|random|set <image>]" >&2
        exit 2
        ;;
esac
