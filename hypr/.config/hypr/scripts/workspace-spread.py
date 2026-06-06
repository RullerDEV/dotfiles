#!/usr/bin/env python3
import sys, struct, threading, time, subprocess, json, os
import glob

kbd_dev = None
mouse_dev = None
speed = 1.0
EVENT_SIZE = struct.calcsize('llHHi')
EV_KEY=1; EV_REL=2; REL_X=0; REL_Y=1
KEY_LEFTMETA=125; KEY_RIGHTMETA=126
KEY_LEFTALT=56; KEY_RIGHTALT=100
KEY_LEFTCTRL=29; KEY_RIGHTCTRL=97
KEY_LEFT=105; KEY_RIGHT=106
BTN_LEFT=272

STATE_FILE = "/tmp/infinite-desktop-state"
LOCK_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "infinite-workspace.lock")
PROTECTED_APPS = ['brave-browser', 'chromium', 'chromium-browser', 'google-chrome',
                  'firefox', 'firefoxdeveloperedition', 'librewolf', 'vivaldi',
                  'opera', 'microsoft-edge']

lock=threading.Lock()
super_pressed=False; alt_pressed=False; ctrl_pressed=False; btn_left=False
acc_x=0.0; acc_y=0.0
last_nav_time = 0
NAV_COOLDOWN = 0.2
prepared_floating = set()

def log(message):
    try:
        print(message, flush=True)
    except BrokenPipeError:
        pass

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE, encoding="utf-8").read().strip())
            os.kill(old_pid, 0)
            log("Infinite Desktop já está rodando.")
            return False
        except:
            pass
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True

def cleanup():
    try:
        os.unlink(LOCK_FILE)
    except:
        pass

def pick_device(kind):
    paths = []
    for base in ("/dev/input/by-id", "/dev/input/by-path"):
        paths.extend(glob.glob(os.path.join(base, "*")))

    paths = sorted(paths)
    if kind == "kbd":
        preferred = [p for p in paths if "event-kbd" in p and "mouse" not in p.lower()]
        fallback = [p for p in paths if "event" in p and "kbd" in p.lower()]
    else:
        preferred = [p for p in paths if "event-mouse" in p]
        fallback = [p for p in paths if p.endswith("-mouse") or "event-if" in p]

    for path in preferred + fallback:
        try:
            return os.path.realpath(path)
        except:
            continue
    return None

def parse_args():
    global kbd_dev, mouse_dev, speed
    if len(sys.argv) >= 4:
        kbd_dev = sys.argv[1]
        mouse_dev = sys.argv[2]
        speed = float(sys.argv[3])
        return

    kbd_dev = pick_device("kbd")
    mouse_dev = pick_device("mouse")
    speed = float(os.environ.get("INFINITE_WORKSPACE_SPEED", "1.0"))

    if not kbd_dev or not mouse_dev:
        log("Uso: workspace-spread.py /dev/input/eventKBD /dev/input/eventMOUSE velocidade")
        log("Não consegui autodetectar teclado/mouse em /dev/input/by-id ou /dev/input/by-path.")
        sys.exit(2)

def read_inverted():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip() == 'inverse'
    except:
        return False

def get_monitor_center():
    try:
        r = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True, text=True, timeout=0.1)
        monitors = json.loads(r.stdout)
        if monitors:
            for m in monitors:
                if m.get('focused', False):
                    x = m['x'] + m['width'] // 2
                    y = m['y'] + m['height'] // 2
                    return x, y
            m = monitors[0]
            x = m['x'] + m['width'] // 2
            y = m['y'] + m['height'] // 2
            return x, y
    except:
        pass
    return 960, 540

def get_workspace_windows(workspace_id, make_floating=False):
    try:
        r = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True, timeout=0.1)
        clients = json.loads(r.stdout)
        windows = []
        for w in clients:
            if w.get('workspace', {}).get('id') != workspace_id:
                continue
            if w.get('fullscreen'):
                continue
            windows.append(w)
            if make_floating and not w.get('floating') and w.get('address') not in prepared_floating:
                prepared_floating.add(w['address'])
                subprocess.Popen(['hyprctl', 'dispatch', 'setfloating', f'address:{w["address"]}'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return windows
    except:
        return []

def get_floating_windows(workspace_id):
    return [w for w in get_workspace_windows(workspace_id) if w.get('floating')]

def get_focused_window():
    try:
        r = subprocess.run(['hyprctl', 'activewindow', '-j'], capture_output=True, text=True, timeout=0.1)
        return json.loads(r.stdout)
    except:
        return None

def is_protected_app(window):
    if not window:
        return False
    window_class = window.get('class', '').lower()
    return any(app in window_class for app in PROTECTED_APPS)

def pan_to_window(floating_windows, target_addr, center_x, center_y):
    target_window = None
    for w in floating_windows:
        if w['address'] == target_addr:
            target_window = w
            break

    if not target_window:
        return

    target_center_x = target_window['at'][0] + target_window['size'][0] // 2
    target_center_y = target_window['at'][1] + target_window['size'][1] // 2

    dx = center_x - target_center_x
    dy = center_y - target_center_y

    for w in floating_windows:
        new_x = w['at'][0] + dx
        new_y = w['at'][1] + dy
        subprocess.Popen(['hyprctl', 'dispatch', 'movewindowpixel',
                         f'exact {int(new_x)} {int(new_y)},address:{w["address"]}'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not is_protected_app(target_window):
        subprocess.Popen(['hyprctl', 'dispatch', 'focuswindow', f'address:{target_addr}'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def change_focus(direction):
    global last_nav_time

    current_time = time.time()
    if current_time - last_nav_time < NAV_COOLDOWN:
        return
    last_nav_time = current_time

    try:
        r = subprocess.run(['hyprctl', 'activeworkspace', '-j'], capture_output=True, text=True, timeout=0.1)
        ws = json.loads(r.stdout)
        workspace_id = ws['id']

        floating_windows = get_workspace_windows(workspace_id, make_floating=True)
        if len(floating_windows) <= 1:
            return

        focused = get_focused_window()
        if not focused or not focused.get('address'):
            if floating_windows:
                center_x, center_y = get_monitor_center()
                first_window = floating_windows[0]
                if is_protected_app(first_window):
                    for w in floating_windows:
                        if not is_protected_app(w):
                            first_window = w
                            break
                pan_to_window(floating_windows, first_window['address'], center_x, center_y)
            return

        current_addr = focused['address']
        current_index = -1
        for i, w in enumerate(floating_windows):
            if w['address'] == current_addr:
                current_index = i
                break

        if current_index == -1:
            return

        if direction == 'right':
            new_index = (current_index + 1) % len(floating_windows)
        else:
            new_index = (current_index - 1) % len(floating_windows)

        new_window = floating_windows[new_index]

        if is_protected_app(new_window):
            attempts = 0
            while is_protected_app(new_window) and attempts < len(floating_windows):
                if direction == 'right':
                    new_index = (new_index + 1) % len(floating_windows)
                else:
                    new_index = (new_index - 1) % len(floating_windows)
                new_window = floating_windows[new_index]
                attempts += 1

            if attempts >= len(floating_windows):
                return

        center_x, center_y = get_monitor_center()
        floating_windows_updated = get_floating_windows(workspace_id)
        pan_to_window(floating_windows_updated, new_window['address'], center_x, center_y)

    except:
        pass

def kbd_reader():
    global super_pressed, alt_pressed, ctrl_pressed

    fd = open(kbd_dev, 'rb')
    while True:
        data = fd.read(EVENT_SIZE)
        if not data or len(data) < EVENT_SIZE:
            break
        _, _, etype, code, value = struct.unpack('llHHi', data)
        if etype != EV_KEY:
            continue
        if value == 2:
            continue

        with lock:
            if code in (KEY_LEFTMETA, KEY_RIGHTMETA):
                super_pressed = (value == 1)
            elif code in (KEY_LEFTALT, KEY_RIGHTALT):
                alt_pressed = (value == 1)
            elif code in (KEY_LEFTCTRL, KEY_RIGHTCTRL):
                ctrl_pressed = (value == 1)

            if ctrl_pressed and super_pressed and not alt_pressed:
                if code == KEY_RIGHT and value == 1:
                    threading.Thread(target=change_focus, args=('right',), daemon=True).start()
                elif code == KEY_LEFT and value == 1:
                    threading.Thread(target=change_focus, args=('left',), daemon=True).start()

def mouse_reader():
    global acc_x, acc_y, btn_left

    fd = open(mouse_dev, 'rb')
    while True:
        data = fd.read(EVENT_SIZE)
        if not data or len(data) < EVENT_SIZE:
            break
        _, _, etype, code, value = struct.unpack('llHHi', data)

        with lock:
            if etype == EV_KEY and code == BTN_LEFT:
                btn_left = (value == 1)
            elif etype == EV_REL:
                if super_pressed and alt_pressed and btn_left:
                    sign = -1 if read_inverted() else 1
                    if code == REL_X:
                        acc_x += value * speed * sign
                    elif code == REL_Y:
                        acc_y += value * speed * sign
                else:
                    if not (super_pressed and alt_pressed and btn_left):
                        acc_x = 0.0
                        acc_y = 0.0

def main():
    global acc_x, acc_y

    if not acquire_lock():
        return

    try:
        parse_args()

        log("Precargando...")
        try:
            subprocess.run(['hyprctl', 'activeworkspace', '-j'], capture_output=True, text=True, timeout=0.5)
            subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True, timeout=0.5)
        except:
            pass
        log(f"¡Listo! Infinite Workspace em {kbd_dev} + {mouse_dev}")

        threading.Thread(target=kbd_reader, daemon=True).start()
        threading.Thread(target=mouse_reader, daemon=True).start()

        log("Infinite Desktop (workspace) - Super+Alt+Mouse1 arrasta | Ctrl+Super+←/→ navega")

        while True:
            time.sleep(0.016)

            with lock:
                active_drag = super_pressed and alt_pressed and btn_left
                dx = acc_x
                dy = acc_y
                acc_x = 0.0
                acc_y = 0.0

            if not active_drag:
                continue

            idx = int(round(dx))
            idy = int(round(dy))

            if idx == 0 and idy == 0:
                continue

            try:
                r = subprocess.run(['hyprctl', 'activeworkspace', '-j'], capture_output=True, text=True, timeout=0.1)
                ws = json.loads(r.stdout)
                workspace_id = ws['id']

                r = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True, timeout=0.1)
                clients = json.loads(r.stdout)

                for w in clients:
                    if w.get('workspace', {}).get('id') != workspace_id:
                        continue
                    if w.get('fullscreen'):
                        continue
                    if not w.get('floating') and w.get('address') not in prepared_floating:
                        prepared_floating.add(w['address'])
                        subprocess.Popen(['hyprctl', 'dispatch', 'setfloating', f'address:{w["address"]}'],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    addr = w['address']
                    nx = w['at'][0] + idx
                    ny = w['at'][1] + idy
                    subprocess.Popen(['hyprctl', 'dispatch', 'movewindowpixel',
                                     f'exact {nx} {ny},address:{addr}'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()
