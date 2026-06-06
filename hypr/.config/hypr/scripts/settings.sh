#!/usr/bin/env bash
set -euo pipefail

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
HYPR_DIR="$CONFIG_HOME/hypr"
SCRIPT_DIR="$HYPR_DIR/scripts"
SETTINGS_FILE="$HYPR_DIR/settings.conf"
PROFILE_FILE="$CACHE_HOME/hypr-profile"
mkdir -p "$CACHE_HOME"

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -a "settings" "settings" "$1" 2>/dev/null || true
    fi
}

restart_waybar() {
    if pgrep -x waybar >/dev/null 2>&1; then
        pkill -SIGUSR2 waybar >/dev/null 2>&1 || true
    elif command -v waybar >/dev/null 2>&1; then
        if command -v hyprctl >/dev/null 2>&1; then
            hyprctl dispatch exec waybar >/dev/null 2>&1 || nohup waybar >/dev/null 2>&1 &
        else
            nohup waybar >/dev/null 2>&1 &
        fi
    fi
}

reload_desktop() {
    if command -v hyprctl >/dev/null 2>&1; then
        hyprctl reload >/dev/null 2>&1 || true
    fi
    restart_waybar
    if pgrep -x swaync >/dev/null 2>&1; then
        swaync-client -rs >/dev/null 2>&1 || true
    fi
}

write_profile() {
    local profile="$1"
    local gaps_in gaps_out border rounding active inactive blur_size blur_passes shadow range
    local noise contrast brightness vibrancy

    case "$profile" in
        clean)
            gaps_in=6; gaps_out=12; border=1; rounding=14; active=0.93; inactive=0.84
            blur_size=7; blur_passes=3; shadow=true; range=20
            noise=0.018; contrast=0.92; brightness=1.04; vibrancy=0.08
            ;;
        glass)
            gaps_in=8; gaps_out=16; border=1; rounding=16; active=0.88; inactive=0.76
            blur_size=10; blur_passes=4; shadow=true; range=26
            noise=0.02; contrast=0.88; brightness=1.08; vibrancy=0.16
            ;;
        focus)
            gaps_in=4; gaps_out=8; border=1; rounding=10; active=1.0; inactive=0.96
            blur_size=4; blur_passes=1; shadow=false; range=10
            noise=0.0; contrast=1.0; brightness=1.0; vibrancy=0.0
            ;;
        solid)
            gaps_in=4; gaps_out=8; border=1; rounding=8; active=1.0; inactive=1.0
            blur_size=0; blur_passes=0; shadow=false; range=0
            noise=0.0; contrast=1.0; brightness=1.0; vibrancy=0.0
            ;;
        *)
            echo "unknown profile: $profile" >&2
            exit 2
            ;;
    esac

    cat > "$SETTINGS_FILE" <<EOF
# Live profile. Managed by ~/.config/hypr/scripts/settings.sh.

general {
    gaps_in = $gaps_in
    gaps_out = $gaps_out
    border_size = $border
    allow_tearing = true
}

decoration {
    rounding = $rounding
    active_opacity = $active
    inactive_opacity = $inactive
    fullscreen_opacity = 1.0

    blur {
        enabled = true
        size = $blur_size
        passes = $blur_passes
        new_optimizations = true
        xray = false
        ignore_opacity = false
        noise = $noise
        contrast = $contrast
        brightness = $brightness
        vibrancy = $vibrancy
        vibrancy_darkness = 0.05
    }

    shadow {
        enabled = $shadow
        range = $range
        render_power = 3
        scale = 0.96
    }
}

animations {
    enabled = true
}

misc {
    animate_manual_resizes = true
    animate_mouse_windowdragging = false
}

cursor {
    no_warps = true
    no_break_fs_vrr = 2
}
EOF

    echo -n "$profile" > "$PROFILE_FILE"
    reload_desktop
    notify "profile: $profile"
}

show_menu() {
    local current_theme current_profile game_state
    current_theme="$(cat "$CACHE_HOME/theme" 2>/dev/null || echo light)"
    current_profile="$(cat "$PROFILE_FILE" 2>/dev/null || echo clean)"
    game_state="$("$SCRIPT_DIR/gamemode.sh" status 2>/dev/null || echo off)"

    printf '%s\n' \
        "profile clean        current: $current_profile" \
        "profile glass" \
        "profile focus" \
        "profile solid" \
        "theme light          current: $current_theme" \
        "theme dark" \
        "theme toggle" \
        "gamemode toggle      current: $game_state" \
        "gamemode on" \
        "gamemode off" \
        "wallpaper next" \
        "resolution toggle" \
        "reload desktop" \
        "restart waybar" \
        "mouse polling status" |
        rofi -dmenu -i -p "settings" -theme "$CONFIG_HOME/rofi/themes/current.rasi"
}

run_action() {
    case "$1" in
        "profile clean"*) write_profile clean ;;
        "profile glass"*) write_profile glass ;;
        "profile focus"*) write_profile focus ;;
        "profile solid"*) write_profile solid ;;
        "theme light"*) "$SCRIPT_DIR/theme-toggle.sh" light ;;
        "theme dark"*) "$SCRIPT_DIR/theme-toggle.sh" dark ;;
        "theme toggle"*) "$SCRIPT_DIR/theme-toggle.sh" toggle ;;
        "gamemode toggle"*) "$SCRIPT_DIR/gamemode.sh" toggle ;;
        "gamemode on"*) "$SCRIPT_DIR/gamemode.sh" on ;;
        "gamemode off"*) "$SCRIPT_DIR/gamemode.sh" off ;;
        "wallpaper next"*) "$SCRIPT_DIR/wallpaper.sh" next ;;
        "resolution toggle"*) "$SCRIPT_DIR/resolution-toggle.sh" toggle ;;
        "reload desktop"*) reload_desktop; notify "desktop reloaded" ;;
        "restart waybar"*) pkill -x waybar 2>/dev/null || true; sleep 0.2; restart_waybar ;;
        "mouse polling status"*) "$SCRIPT_DIR/mouse-1000hz.sh" status | rofi -dmenu -p "mouse" -theme "$CONFIG_HOME/rofi/themes/current.rasi" >/dev/null ;;
        "") exit 0 ;;
    esac
}

case "${1:-menu}" in
    menu)
        choice="$(show_menu || true)"
        run_action "$choice"
        ;;
    profile)
        write_profile "${2:-clean}"
        ;;
    reload)
        reload_desktop
        ;;
    *)
        echo "usage: $0 [menu|profile clean|profile glass|profile focus|profile solid|reload]" >&2
        exit 2
        ;;
esac
