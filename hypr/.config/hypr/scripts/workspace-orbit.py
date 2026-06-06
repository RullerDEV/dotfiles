#!/usr/bin/env python3
import html
import json
import math
import os
import random
import signal
import subprocess
import sys
import time

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell


RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
LOCK_FILE = os.path.join(RUNTIME_DIR, "workspace-orbit.lock")
WORKSPACE_COUNT = 9


def hypr_json(*args, fallback):
    try:
        out = subprocess.check_output(["hyprctl", *args, "-j"], text=True, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception:
        return fallback


def hypr_dispatch(*args):
    subprocess.Popen(["hyprctl", "dispatch", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def clamp(value, low, high):
    return max(low, min(high, value))


def color(cr, hex_color, alpha=1.0):
    h = hex_color.lstrip("#")
    cr.set_source_rgba(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)


def rounded_rect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def app_icon(app_class, title):
    text = f"{app_class or ''} {title or ''}".lower()
    rules = [
        ("brave|chrome|chromium|firefox|browser", "󰖟"),
        ("code|vscode|codium", "󰨞"),
        ("kitty|foot|alacritty|wezterm|terminal", ""),
        ("discord|vesktop", "󰙯"),
        ("spotify", ""),
        ("steam", ""),
        ("heroic|lutris|wine|game", "󰊴"),
        ("yazi|thunar|nautilus|dolphin|file", "󰉋"),
        ("pavucontrol|audio|volume", "󰕾"),
        ("rofi", "󰍉"),
    ]
    for pattern, icon in rules:
        if any(piece in text for piece in pattern.split("|")):
            return icon
    return "󰣆"


class WorkspaceOrbit(Gtk.Window):
    def __init__(self):
        super().__init__(title="workspace-orbit")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_interactivity(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_exclusive_zone(self, -1)

        self.area = Gtk.DrawingArea()
        self.add(self.area)
        self.area.set_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.SCROLL_MASK
        )

        self.area.connect("draw", self.draw)
        self.area.connect("motion-notify-event", self.on_motion)
        self.area.connect("button-press-event", self.on_click)
        self.area.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", self.cleanup)

        self.started = time.monotonic()
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.selected = 0
        self.hitboxes = []
        self.refresh()

        GLib.timeout_add(16, self.tick)
        GLib.timeout_add(1000, self.refresh_timer)

    def refresh_timer(self):
        self.refresh()
        return True

    def refresh(self):
        old_id = None
        if getattr(self, "workspaces", None):
            old_id = int(self.workspaces[self.selected].get("id", 0))

        active = hypr_json("activeworkspace", fallback={"id": 1})
        workspaces = hypr_json("workspaces", fallback=[])
        clients = hypr_json("clients", fallback=[])

        known = {i: {"id": i, "name": str(i), "windows": 0, "monitor": ""} for i in range(1, WORKSPACE_COUNT + 1)}
        for ws in workspaces:
            wid = int(ws.get("id", 0) or 0)
            if wid > 0:
                known[wid] = ws

        grouped = {wid: [] for wid in known}
        for client in clients:
            wid = int(client.get("workspace", {}).get("id", 0) or 0)
            if wid <= 0:
                continue
            grouped.setdefault(wid, [])
            grouped[wid].append(client)
            known.setdefault(wid, {"id": wid, "name": str(wid), "windows": 0, "monitor": ""})

        self.workspaces = [known[k] for k in sorted(known) if k > 0]
        self.grouped = grouped
        active_id = int(active.get("id", 1) or 1)
        ids = [int(ws.get("id", 0)) for ws in self.workspaces]
        if old_id in ids:
            self.selected = ids.index(old_id)
        elif active_id in ids:
            self.selected = ids.index(active_id)

    def tick(self):
        self.mouse_x += (self.target_x - self.mouse_x) * 0.08
        self.mouse_y += (self.target_y - self.mouse_y) * 0.08
        self.area.queue_draw()
        return True

    def cleanup(self, *_):
        try:
            os.unlink(LOCK_FILE)
        except FileNotFoundError:
            pass

    def close(self):
        self.destroy()
        Gtk.main_quit()

    def on_motion(self, _widget, event):
        width = max(1, self.area.get_allocated_width())
        height = max(1, self.area.get_allocated_height())
        self.target_x = (event.x / width - 0.5) * 2
        self.target_y = (event.y / height - 0.5) * 2
        return True

    def on_scroll(self, _widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.move_selection(-1)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.move_selection(1)
        return True

    def on_click(self, _widget, event):
        for wid, x, y, w, h in reversed(self.hitboxes):
            if x <= event.x <= x + w and y <= event.y <= y + h:
                hypr_dispatch("workspace", str(wid))
                self.close()
                return True
        return True

    def on_key(self, _widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key in ("Escape", "q"):
            self.close()
        elif key in ("Right", "Down", "Tab", "space"):
            self.move_selection(1)
        elif key in ("Left", "Up", "ISO_Left_Tab"):
            self.move_selection(-1)
        elif key in ("Return", "KP_Enter"):
            wid = int(self.workspaces[self.selected].get("id", 1))
            hypr_dispatch("workspace", str(wid))
            self.close()
        elif key and key.isdigit() and key != "0":
            hypr_dispatch("workspace", key)
            self.close()
        return True

    def move_selection(self, direction):
        if not self.workspaces:
            return
        self.selected = (self.selected + direction) % len(self.workspaces)

    def draw_text(self, cr, text, x, y, size=14, weight=cairo.FONT_WEIGHT_NORMAL, alpha=1.0, max_width=None):
        cr.save()
        color(cr, "#24231f", alpha)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, weight)
        cr.set_font_size(size)
        shown = str(text)
        if max_width:
            while shown and cr.text_extents(shown + "...").width > max_width:
                shown = shown[:-1]
            if shown != str(text):
                shown += "..."
        cr.move_to(x, y)
        cr.show_text(shown)
        cr.restore()

    def workspace_center(self, index, total, width, height, now):
        cx = width / 2
        cy = height / 2 + 20
        radius_x = min(width * 0.37, 520)
        radius_y = min(height * 0.24, 210)
        base = -math.pi / 2
        angle = base + (index - self.selected) * (2 * math.pi / max(total, 1)) + self.mouse_x * 0.38
        tilt = self.mouse_y * 34
        depth = (math.sin(angle) + 1) / 2
        x = cx + math.cos(angle) * radius_x
        y = cy + math.sin(angle) * radius_y * 0.72 + tilt + math.sin(now * 1.2 + index) * 5
        scale = 0.74 + depth * 0.32
        return x, y, scale, depth

    def draw(self, _widget, cr):
        width = self.area.get_allocated_width()
        height = self.area.get_allocated_height()
        now = time.monotonic() - self.started
        self.hitboxes = []

        color(cr, "#0f1110", 0.48)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        gradient = cairo.RadialGradient(width / 2, height * 0.45, 40, width / 2, height * 0.45, max(width, height) * 0.75)
        gradient.add_color_stop_rgba(0, 0.96, 0.94, 0.88, 0.30)
        gradient.add_color_stop_rgba(1, 0.06, 0.07, 0.06, 0.05)
        cr.set_source(gradient)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        self.draw_text(cr, "workspace orbit", 42, 52, 18, cairo.FONT_WEIGHT_BOLD, 0.92)
        self.draw_text(cr, "arrows navigate   enter opens   esc quits", 42, 78, 11, cairo.FONT_WEIGHT_NORMAL, 0.62)
        cr.restore()

        items = []
        total = len(self.workspaces)
        for i, ws in enumerate(self.workspaces):
            x, y, scale, depth = self.workspace_center(i, total, width, height, now)
            items.append((depth, i, ws, x, y, scale))

        for _depth, i, ws, x, y, scale in sorted(items):
            self.draw_workspace(cr, i, ws, x, y, scale, now)

        return False

    def draw_workspace(self, cr, index, ws, cx, cy, scale, now):
        wid = int(ws.get("id", index + 1))
        clients = self.grouped.get(wid, [])
        selected = index == self.selected
        card_w = (230 if selected else 196) * scale
        card_h = (132 if selected else 108) * scale
        x = cx - card_w / 2
        y = cy - card_h / 2
        alpha = 0.94 if selected else 0.70

        cr.save()
        color(cr, "#000000", 0.12 * scale)
        rounded_rect(cr, x + 8, y + 10, card_w, card_h, 18 * scale)
        cr.fill()

        color(cr, "#fbfaf6", alpha)
        rounded_rect(cr, x, y, card_w, card_h, 18 * scale)
        cr.fill()
        color(cr, "#2d3530" if selected else "#d5ccbf", 0.75 if selected else 0.55)
        cr.set_line_width(1.4 if selected else 1.0)
        rounded_rect(cr, x, y, card_w, card_h, 18 * scale)
        cr.stroke()

        self.hitboxes.append((wid, x, y, card_w, card_h))

        color(cr, "#2d3530", 1.0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(26 * scale)
        cr.move_to(x + 18 * scale, y + 38 * scale)
        cr.show_text(str(wid))

        label = f"{len(clients)} window" + ("" if len(clients) == 1 else "s")
        self.draw_text(cr, label, x + 58 * scale, y + 31 * scale, 10 * scale, cairo.FONT_WEIGHT_BOLD, 0.64)

        if not clients:
            self.draw_text(cr, "empty", x + 18 * scale, y + 78 * scale, 14 * scale, cairo.FONT_WEIGHT_NORMAL, 0.45)
        else:
            for n, client in enumerate(clients[:4]):
                seed = hash(client.get("address", f"{wid}-{n}")) & 0xFFFF
                rng = random.Random(seed)
                ox = (rng.random() - 0.5) * 18 * scale
                oy = math.sin(now * (0.9 + rng.random()) + rng.random() * 6.2) * 4 * scale
                row_y = y + (62 + n * 18) * scale + oy
                icon = app_icon(client.get("class"), client.get("title"))
                color(cr, "#e7e1d7", 0.86)
                rounded_rect(cr, x + 16 * scale + ox, row_y - 12 * scale, card_w - 32 * scale, 15 * scale, 7 * scale)
                cr.fill()
                self.draw_text(cr, icon, x + 24 * scale + ox, row_y, 10 * scale, cairo.FONT_WEIGHT_BOLD, 0.95)
                title = html.unescape(client.get("title") or client.get("class") or "window")
                self.draw_text(cr, title, x + 46 * scale + ox, row_y, 9.2 * scale, cairo.FONT_WEIGHT_NORMAL, 0.72, card_w - 68 * scale)
        cr.restore()


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE).read().strip())
            os.kill(old_pid, 0)
            return False
        except Exception:
            pass
    with open(LOCK_FILE, "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    return True


def main():
    if not acquire_lock():
        sys.exit(0)
    win = WorkspaceOrbit()
    signal.signal(signal.SIGTERM, lambda *_args: win.close())
    signal.signal(signal.SIGINT, lambda *_args: win.close())
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
