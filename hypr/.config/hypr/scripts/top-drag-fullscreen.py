#!/usr/bin/env python3
import json
import subprocess
import sys


TOP_GRAB_MARGIN = 18


def hypr_json(*args):
    out = subprocess.check_output(["hyprctl", "-j", *args], text=True)
    return json.loads(out)


def hypr(*args):
    subprocess.run(["hyprctl", *args], check=False)


def active_monitor(monitors, monitor_id):
    for monitor in monitors:
        if monitor.get("id") == monitor_id:
            return monitor
    return None


def check_top_drag():
    try:
        window = hypr_json("activewindow")
        if not window or not window.get("mapped"):
            return

        if window.get("fullscreen", 0):
            return

        if not window.get("floating", False):
            return

        monitors = hypr_json("monitors")
        monitor = active_monitor(monitors, window.get("monitor"))
        if not monitor:
            return

        reserved = monitor.get("reserved", [0, 0, 0, 0])
        reserved_top = reserved[1] if len(reserved) > 1 else 0
        top_edge = monitor.get("y", 0) + reserved_top
        window_top = window.get("at", [0, 0])[1]

        if window_top <= top_edge + TOP_GRAB_MARGIN:
            hypr("dispatch", "fullscreen", "1")
    except Exception:
        return


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "check":
        check_top_drag()
