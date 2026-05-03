#!/usr/bin/env bash
set -euo pipefail

mode="${1:-area}"
post="${2:-}"
outdir="${SCREENSHOT_DIR:-$HOME/Imagem}"
mkdir -p "$outdir"
outfile="$outdir/screenshot_$(date +%Y%m%d_%H%M%S).png"

case "$mode" in
    area)
        geo="$(slurp -d -c fafafaff -b 0a0a0a88)" || exit 0
        [ -n "$geo" ] || exit 0
        grim -g "$geo" "$outfile"
        ;;
    full)
        grim "$outfile"
        ;;
    window)
        if ! command -v hyprctl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
            echo "window mode requires hyprctl + jq" >&2
            exit 1
        fi
        geo="$(hyprctl activewindow -j | jq -r '"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')"
        [ -n "$geo" ] || exit 1
        grim -g "$geo" "$outfile"
        ;;
    *)
        echo "usage: $0 [area|full|window] [edit]" >&2
        exit 1
        ;;
esac

if [ "$post" = "edit" ] && command -v swappy >/dev/null 2>&1; then
    swappy -f "$outfile" -o "$outfile"
fi

wl-copy --type image/png < "$outfile"

if command -v notify-send >/dev/null 2>&1; then
    notify-send -i "$outfile" "screenshot" "copiado e salvo em\n$outfile"
fi
