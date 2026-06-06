#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="$DIR/m1_m4_macro.c"
BIN="$DIR/m1_m4_macro"
PID="${XDG_RUNTIME_DIR:-/tmp}/m1_m4_macro.pid"
LOG="${XDG_RUNTIME_DIR:-/tmp}/m1_m4_macro.log"
FLAG="/tmp/gamemode"

build() {
    if [ ! -x "$BIN" ] || [ "$SRC" -nt "$BIN" ]; then
        cc -std=gnu11 -O2 -pipe -pthread -Wall -Wextra -o "$BIN" "$SRC"
    fi
}

is_running() {
    [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null
}

start() {
    build

    if is_running; then
        exit 0
    fi

    if [ -n "${1:-}" ]; then
        M1_M4_FLAG="$FLAG" nohup "$BIN" "$1" >"$LOG" 2>&1 &
    else
        M1_M4_FLAG="$FLAG" nohup "$BIN" >"$LOG" 2>&1 &
    fi
    echo "$!" >"$PID"
}

stop() {
    if is_running; then
        kill "$(cat "$PID")" 2>/dev/null || true
    fi
    rm -f "$PID"
}

status() {
    if is_running; then
        echo "m1_m4_macro: running pid $(cat "$PID")"
    else
        echo "m1_m4_macro: stopped"
    fi
}

case "${1:-start}" in
    start)
        start "${2:-}"
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start "${2:-}"
        ;;
    status)
        status
        ;;
    build)
        build
        ;;
    *)
        echo "usage: $0 [start|stop|restart|status|build] [/dev/input/eventN]" >&2
        exit 2
        ;;
esac
