#!/usr/bin/env python3
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell


RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
LOCK_FILE = os.path.join(RUNTIME_DIR, "workspace-preview.lock")
TMP_DIR = os.path.join(tempfile.gettempdir(), f"workspace-preview-{os.getpid()}")
WORKSPACE_LIMIT = 9


def hypr_json(command, fallback):
    try:
        raw = subprocess.check_output(["hyprctl", command, "-j"], text=True, stderr=subprocess.DEVNULL)
        return json.loads(raw)
    except Exception:
        return fallback


def dispatch(*args):
    subprocess.run(["hyprctl", "dispatch", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)


def color(cr, value, alpha=1.0):
    value = value.lstrip("#")
    cr.set_source_rgba(int(value[0:2], 16) / 255, int(value[2:4], 16) / 255, int(value[4:6], 16) / 255, alpha)


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
        (("brave", "chrome", "chromium", "firefox"), "󰖟"),
        (("code", "vscode", "codium"), "󰨞"),
        (("kitty", "terminal", "wezterm", "alacritty"), ""),
        (("discord", "vesktop"), "󰙯"),
        (("spotify",), ""),
        (("steam",), ""),
        (("heroic", "lutris", "wine", "game"), "󰊴"),
        (("yazi", "thunar", "nautilus", "dolphin", "file"), "󰉋"),
    ]
    for keys, icon in rules:
        if any(k in text for k in keys):
            return icon
    return "󰣆"


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE, encoding="utf-8").read().strip())
            os.kill(old_pid, 0)
            return False
        except Exception:
            pass
    with open(LOCK_FILE, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return True


def cleanup():
    try:
        os.unlink(LOCK_FILE)
    except FileNotFoundError:
        pass
    shutil.rmtree(TMP_DIR, ignore_errors=True)


def snapshot_workspaces():
    os.makedirs(TMP_DIR, exist_ok=True)
    monitors = hypr_json("monitors", [])
    workspaces = hypr_json("workspaces", [])
    clients = hypr_json("clients", [])
    active = hypr_json("activeworkspace", {"id": 1})

    clients_by_ws = {}
    for client in clients:
        wid = int(client.get("workspace", {}).get("id", 0) or 0)
        if wid > 0:
            clients_by_ws.setdefault(wid, []).append(client)

    occupied = []
    for ws in sorted(workspaces, key=lambda item: int(item.get("id", 0) or 0)):
        wid = int(ws.get("id", 0) or 0)
        if 0 < wid <= WORKSPACE_LIMIT and clients_by_ws.get(wid):
            occupied.append(ws)

    original_monitor = next((m.get("name") for m in monitors if m.get("focused")), None)
    original_by_monitor = {
        m.get("name"): int(m.get("activeWorkspace", {}).get("id", 1) or 1)
        for m in monitors
        if m.get("name")
    }

    grim = shutil.which("grim")
    previews = []
    try:
        for ws in occupied:
            wid = int(ws.get("id"))
            monitor = ws.get("monitor") or original_monitor
            path = os.path.join(TMP_DIR, f"workspace-{wid}.png")

            if monitor:
                dispatch("focusmonitor", monitor)
            dispatch("workspace", str(wid))
            time.sleep(0.12)

            captured = False
            if grim and monitor:
                captured = subprocess.run(["grim", "-o", monitor, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if grim and not captured:
                captured = subprocess.run(["grim", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

            previews.append({
                "id": wid,
                "monitor": monitor or "",
                "clients": clients_by_ws.get(wid, []),
                "path": path if captured and os.path.exists(path) else None,
            })
    finally:
        for monitor, wid in original_by_monitor.items():
            dispatch("focusmonitor", monitor)
            dispatch("workspace", str(wid))
        if original_monitor:
            dispatch("focusmonitor", original_monitor)
        elif active.get("id"):
            dispatch("workspace", str(active.get("id")))

    return previews


class PreviewWindow(Gtk.Window):
    def __init__(self, previews):
        super().__init__(title="workspace-preview")
        self.previews = previews
        self.selected = 0
        self.hovered = None
        self.hitboxes = []
        self.started = time.monotonic()
        self.pixbufs = {}

        for preview in previews:
            if preview["path"]:
                try:
                    self.pixbufs[preview["id"]] = GdkPixbuf.Pixbuf.new_from_file(preview["path"])
                except Exception:
                    pass

        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_interactivity(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT):
            GtkLayerShell.set_anchor(self, edge, True)

        self.area = Gtk.DrawingArea()
        self.add(self.area)
        self.area.set_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.area.connect("draw", self.draw)
        self.area.connect("motion-notify-event", self.on_motion)
        self.area.connect("button-press-event", self.on_click)
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", lambda *_: cleanup())
        GLib.timeout_add(16, self.animate_in)

    def animate_in(self):
        self.area.queue_draw()
        return time.monotonic() - self.started < 0.28

    def close(self):
        self.destroy()
        Gtk.main_quit()

    def focus_selected(self):
        if self.previews:
            dispatch("workspace", str(self.previews[self.selected]["id"]))
        self.close()

    def on_key(self, _widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key in ("Escape", "q"):
            self.close()
        elif key in ("Right", "Down", "Tab", "space"):
            self.selected = (self.selected + 1) % max(1, len(self.previews))
            self.area.queue_draw()
        elif key in ("Left", "Up", "ISO_Left_Tab"):
            self.selected = (self.selected - 1) % max(1, len(self.previews))
            self.area.queue_draw()
        elif key in ("Return", "KP_Enter"):
            self.focus_selected()
        elif key and key.isdigit():
            for i, preview in enumerate(self.previews):
                if str(preview["id"]) == key:
                    self.selected = i
                    self.focus_selected()
                    break
        return True

    def on_motion(self, _widget, event):
        self.hovered = None
        for i, (_wid, x, y, w, h) in enumerate(self.hitboxes):
            if x <= event.x <= x + w and y <= event.y <= y + h:
                self.hovered = i
                break
        self.area.queue_draw()
        return True

    def on_click(self, _widget, event):
        for i, (_wid, x, y, w, h) in enumerate(self.hitboxes):
            if x <= event.x <= x + w and y <= event.y <= y + h:
                self.selected = i
                self.focus_selected()
                return True
        return True

    def text(self, cr, value, x, y, size, weight=cairo.FONT_WEIGHT_NORMAL, alpha=1.0, max_width=None):
        shown = str(value)
        cr.save()
        color(cr, "#f4f1ea", alpha)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, weight)
        cr.set_font_size(size)
        if max_width:
            while shown and cr.text_extents(shown + "...").width > max_width:
                shown = shown[:-1]
            if shown != str(value):
                shown += "..."
        cr.move_to(x, y)
        cr.show_text(shown)
        cr.restore()

    def layout(self, width, height):
        count = max(1, len(self.previews))
        cols = min(3, count)
        rows = math.ceil(count / cols)
        gap = 28
        card_w = min(470, (width - 120 - gap * (cols - 1)) / cols)
        if count == 1:
            card_w = min(620, width * 0.62)
        card_h = card_w * 0.56 + 86
        start_x = (width - (cols * card_w + (cols - 1) * gap)) / 2
        start_y = max(112, (height - (rows * card_h + (rows - 1) * gap)) / 2 + 20)
        return cols, gap, card_w, card_h, start_x, start_y

    def draw(self, _widget, cr):
        width = self.area.get_allocated_width()
        height = self.area.get_allocated_height()
        progress = min(1.0, (time.monotonic() - self.started) / 0.20)
        alpha = 1 - (1 - progress) ** 3
        self.hitboxes = []

        color(cr, "#0f1110", 0.72 * alpha)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        self.text(cr, "workspace preview", 42, 52, 18, cairo.FONT_WEIGHT_BOLD, 0.95 * alpha)
        self.text(cr, "only occupied workspaces   arrows navigate   enter opens   esc quits", 42, 76, 11, cairo.FONT_WEIGHT_NORMAL, 0.60 * alpha)

        if not self.previews:
            self.text(cr, "no occupied workspaces", width / 2 - 110, height / 2, 18, cairo.FONT_WEIGHT_BOLD, 0.82 * alpha)
            return False

        cols, gap, card_w, card_h, start_x, start_y = self.layout(width, height)
        for i, preview in enumerate(self.previews):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap) + (1 - alpha) * 16
            self.draw_card(cr, preview, i, x, y, card_w, card_h, i == self.selected or i == self.hovered, alpha)
        return False

    def draw_card(self, cr, preview, index, x, y, w, h, hot, alpha):
        wid = preview["id"]
        preview_h = w * 0.56
        self.hitboxes.append((wid, x, y, w, h))

        color(cr, "#000000", 0.22 * alpha)
        rounded_rect(cr, x + 8, y + 10, w, h, 14)
        cr.fill()

        color(cr, "#171a18", 0.90 * alpha)
        rounded_rect(cr, x, y, w, h, 14)
        cr.fill()

        color(cr, "#f4f1ea" if hot else "#353a34", 0.95 if hot else 0.82)
        cr.set_line_width(1.6 if hot else 1.0)
        rounded_rect(cr, x, y, w, h, 14)
        cr.stroke()

        pixbuf = self.pixbufs.get(wid)
        if pixbuf:
            img_w, img_h = pixbuf.get_width(), pixbuf.get_height()
            scale = max((w - 20) / img_w, preview_h / img_h)
            draw_w, draw_h = img_w * scale, img_h * scale
            px = x + 10 + ((w - 20) - draw_w) / 2
            py = y + 42 + (preview_h - draw_h) / 2
            cr.save()
            rounded_rect(cr, x + 10, y + 42, w - 20, preview_h, 10)
            cr.clip()
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, pixbuf, px / scale, py / scale)
            cr.paint_with_alpha(0.97 * alpha)
            cr.restore()
        else:
            color(cr, "#242925", 0.90 * alpha)
            rounded_rect(cr, x + 10, y + 42, w - 20, preview_h, 10)
            cr.fill()
            self.text(cr, "screenshot unavailable", x + 24, y + 42 + preview_h / 2, 13, cairo.FONT_WEIGHT_NORMAL, 0.55 * alpha)

        self.text(cr, str(wid), x + 16, y + 27, 18, cairo.FONT_WEIGHT_BOLD, alpha)
        count = len(preview["clients"])
        self.text(cr, f"{count} window" + ("" if count == 1 else "s"), x + 48, y + 26, 11, cairo.FONT_WEIGHT_BOLD, 0.72 * alpha)
        self.text(cr, preview["monitor"], x + w - 106, y + 26, 10, cairo.FONT_WEIGHT_NORMAL, 0.42 * alpha, 90)

        footer_y = y + 42 + preview_h + 30
        icons = "  ".join(app_icon(c.get("class"), c.get("title")) for c in preview["clients"][:6])
        first_title = preview["clients"][0].get("title") or preview["clients"][0].get("class") or ""
        self.text(cr, icons, x + 16, footer_y, 13, cairo.FONT_WEIGHT_BOLD, 0.86 * alpha, w * 0.30)
        self.text(cr, first_title, x + 96, footer_y, 11, cairo.FONT_WEIGHT_NORMAL, 0.62 * alpha, w - 116)


def main():
    if not acquire_lock():
        return

    signal.signal(signal.SIGTERM, lambda *_: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda *_: (cleanup(), sys.exit(0)))

    previews = snapshot_workspaces()
    window = PreviewWindow(previews)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
