#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${SPOTIFY_WORKSPACE:-9}"
PLAYER="spotify"
CLASS='class:^(spotify)$'
CONF="$HOME/.config/spotify/quickplay.conf"
PLAYLIST_URI="${SPOTIFY_PLAYLIST_URI:-}"
API_HELPER="$HOME/.local/bin/spotify-webapi-play"

if [ -f "$CONF" ]; then
    # shellcheck disable=SC1090
    . "$CONF"
fi

ensure_running() {
    if ! playerctl -l 2>/dev/null | grep -qx "$PLAYER"; then
        hyprctl dispatch exec "[workspace $WORKSPACE silent] spotify"
        for _ in $(seq 1 30); do
            if playerctl -l 2>/dev/null | grep -qx "$PLAYER"; then
                break
            fi
            sleep 0.5
        done
    fi
}

move_to_workspace() {
    hyprctl dispatch movetoworkspacesilent "$WORKSPACE,$CLASS" >/dev/null 2>&1 || true
}

send_spotify_key() {
    local key="$1"
    hyprctl dispatch sendshortcut ", $key, $CLASS" >/dev/null 2>&1 || true
}

prime_playlist_ui() {
    # Your Spotify flow requires selecting the first track in the playlist view
    # before playback actually starts.
    send_spotify_key ALT_L
    sleep 0.3
    send_spotify_key RETURN
    sleep 0.6
}

play_target() {
    if [ -x "$API_HELPER" ] && "$API_HELPER"; then
        return 0
    fi

    if [ -n "${PLAYLIST_URI:-}" ]; then
        playerctl --player="$PLAYER" open "$PLAYLIST_URI" >/dev/null 2>&1 || true
        sleep 2
        prime_playlist_ui
    fi

    playerctl --player="$PLAYER" volume 1 >/dev/null 2>&1 || true

    for _ in $(seq 1 10); do
        playerctl --player="$PLAYER" play >/dev/null 2>&1 || true
        sleep 0.5
        if [ "$(playerctl --player="$PLAYER" status 2>/dev/null || true)" = "Playing" ]; then
            return 0
        fi
    done

    for _ in $(seq 1 6); do
        playerctl --player="$PLAYER" play-pause >/dev/null 2>&1 || true
        sleep 0.5
        if [ "$(playerctl --player="$PLAYER" status 2>/dev/null || true)" = "Playing" ]; then
            return 0
        fi
    done
}

ensure_running
move_to_workspace
play_target
