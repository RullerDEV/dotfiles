#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${DISCORD_WORKSPACE:-7}"
CLASS='class:^(discord)$'

if hyprctl clients -j | grep -q '"class": "discord"'; then
    hyprctl dispatch workspace "$WORKSPACE" >/dev/null 2>&1 || true
    hyprctl dispatch focuswindow "$CLASS" >/dev/null 2>&1 || true
    exit 0
fi

hyprctl dispatch exec "[workspace $WORKSPACE silent] /home/felipe/.local/bin/discord-wrapper"
