#!/usr/bin/env bash
set -euo pipefail

CONF="/etc/modprobe.d/usbhid-1000hz.conf"
LINE="options usbhid mousepoll=1"

case "${1:-show}" in
    show|status)
        if [ -r /sys/module/usbhid/parameters/mousepoll ]; then
            echo "mousepoll atual: $(cat /sys/module/usbhid/parameters/mousepoll)"
        else
            echo "mousepoll atual: indisponivel"
        fi
        if [ -f "$CONF" ]; then
            echo "$CONF:"
            cat "$CONF"
        fi
        ;;
    install)
        if [ "${EUID:-$(id -u)}" -ne 0 ]; then
            echo "rode com sudo: sudo $0 install" >&2
            exit 1
        fi
        printf '%s\n' "$LINE" > "$CONF"
        echo "gravado: $CONF"
        echo "reinicie para garantir 1000Hz no driver usbhid"
        ;;
    *)
        echo "usage: $0 [show|install]" >&2
        exit 2
        ;;
esac
