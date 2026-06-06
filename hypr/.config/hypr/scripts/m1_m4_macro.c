#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#define BITS_PER_LONG (sizeof(unsigned long) * 8)
#define NBITS(x) ((((x) - 1) / BITS_PER_LONG) + 1)
#define TEST_BIT(bit, array) (((array)[(bit) / BITS_PER_LONG] >> ((bit) % BITS_PER_LONG)) & 1UL)

static const char *flag_path = "/tmp/gamemode";
static atomic_bool running = true;
static atomic_bool macro_allowed = false;
static atomic_bool hypr_ready = false;

static void on_signal(int sig) {
    (void)sig;
    atomic_store(&running, false);
}

static bool path_exists(const char *path) {
    return access(path, F_OK) == 0;
}

static int connect_unix_socket(const char *path) {
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", path);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }

    return fd;
}

static bool json_has_true_or_one(const char *json, const char *key) {
    const char *p = strstr(json, key);
    if (!p) return false;

    p = strchr(p, ':');
    if (!p) return false;
    p++;

    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;

    if (strncmp(p, "true", 4) == 0) return true;
    if (*p >= '1' && *p <= '9') return true;
    return false;
}

static bool hypr_active_fullscreen(void) {
    const char *runtime = getenv("XDG_RUNTIME_DIR");
    const char *sig = getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if (!runtime || !sig || !*runtime || !*sig) return false;

    char socket_path[512];
    snprintf(socket_path, sizeof(socket_path), "%s/hypr/%s/.socket.sock", runtime, sig);

    int fd = connect_unix_socket(socket_path);
    if (fd < 0) return false;

    const char req[] = "j/activewindow";
    ssize_t written = write(fd, req, sizeof(req) - 1);
    if (written < 0) {
        close(fd);
        return false;
    }

    char buf[8192];
    ssize_t total = 0;
    for (;;) {
        ssize_t n = read(fd, buf + total, sizeof(buf) - 1 - (size_t)total);
        if (n <= 0) break;
        total += n;
        if ((size_t)total >= sizeof(buf) - 1) break;
    }

    close(fd);
    if (total <= 0) return false;
    buf[total] = '\0';

    atomic_store(&hypr_ready, true);
    return json_has_true_or_one(buf, "\"fullscreen\"") || json_has_true_or_one(buf, "\"fullscreenMode\"");
}

static void sleep_ms(long ms) {
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

static void *state_thread(void *arg) {
    (void)arg;

    while (atomic_load(&running)) {
        bool allowed = path_exists(flag_path) && hypr_active_fullscreen();
        atomic_store(&macro_allowed, allowed);
        sleep_ms(80);
    }

    atomic_store(&macro_allowed, false);
    return NULL;
}

static bool get_bits(int fd, int ev, unsigned long *bits, size_t bytes) {
    memset(bits, 0, bytes);
    return ioctl(fd, EVIOCGBIT(ev, bytes), bits) >= 0;
}

static bool has_key(int fd, int code) {
    unsigned long bits[NBITS(KEY_MAX + 1)];
    if (!get_bits(fd, EV_KEY, bits, sizeof(bits))) return false;
    return TEST_BIT(code, bits);
}

static bool has_rel(int fd, int code) {
    unsigned long bits[NBITS(REL_MAX + 1)];
    if (!get_bits(fd, EV_REL, bits, sizeof(bits))) return false;
    return TEST_BIT(code, bits);
}

static bool looks_like_mouse(int fd) {
    return has_key(fd, BTN_RIGHT) && has_rel(fd, REL_X) && has_rel(fd, REL_Y);
}

static bool has_macro_button(int fd) {
    return has_key(fd, BTN_SIDE);
}

static int find_mouse(char *out, size_t out_size) {
    DIR *dir = opendir("/dev/input");
    if (!dir) return -1;

    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        if (strncmp(ent->d_name, "event", 5) != 0) continue;

        char path[256];
        snprintf(path, sizeof(path), "/dev/input/%s", ent->d_name);

        int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) continue;

        bool ok = looks_like_mouse(fd) && has_macro_button(fd);
        close(fd);

        if (ok) {
            snprintf(out, out_size, "%s", path);
            closedir(dir);
            return 0;
        }
    }

    closedir(dir);
    return -1;
}

static void setup_capabilities(int src, int ufd) {
    unsigned long ev_bits[NBITS(EV_MAX + 1)];
    unsigned long key_bits[NBITS(KEY_MAX + 1)];
    unsigned long rel_bits[NBITS(REL_MAX + 1)];
    unsigned long abs_bits[NBITS(ABS_MAX + 1)];
    unsigned long msc_bits[NBITS(MSC_MAX + 1)];

    get_bits(src, 0, ev_bits, sizeof(ev_bits));

    ioctl(ufd, UI_SET_EVBIT, EV_SYN);

    if (TEST_BIT(EV_KEY, ev_bits) && get_bits(src, EV_KEY, key_bits, sizeof(key_bits))) {
        ioctl(ufd, UI_SET_EVBIT, EV_KEY);
        for (int i = 0; i <= KEY_MAX; i++) {
            if (TEST_BIT(i, key_bits)) ioctl(ufd, UI_SET_KEYBIT, i);
        }
    }

    ioctl(ufd, UI_SET_KEYBIT, BTN_RIGHT);
    ioctl(ufd, UI_SET_KEYBIT, BTN_SIDE);

    if (TEST_BIT(EV_REL, ev_bits) && get_bits(src, EV_REL, rel_bits, sizeof(rel_bits))) {
        ioctl(ufd, UI_SET_EVBIT, EV_REL);
        for (int i = 0; i <= REL_MAX; i++) {
            if (TEST_BIT(i, rel_bits)) ioctl(ufd, UI_SET_RELBIT, i);
        }
    }

    if (TEST_BIT(EV_ABS, ev_bits) && get_bits(src, EV_ABS, abs_bits, sizeof(abs_bits))) {
        ioctl(ufd, UI_SET_EVBIT, EV_ABS);
        for (int i = 0; i <= ABS_MAX; i++) {
            if (TEST_BIT(i, abs_bits)) ioctl(ufd, UI_SET_ABSBIT, i);
        }
    }

    if (TEST_BIT(EV_MSC, ev_bits) && get_bits(src, EV_MSC, msc_bits, sizeof(msc_bits))) {
        ioctl(ufd, UI_SET_EVBIT, EV_MSC);
        for (int i = 0; i <= MSC_MAX; i++) {
            if (TEST_BIT(i, msc_bits)) ioctl(ufd, UI_SET_MSCBIT, i);
        }
    }
}

static int create_uinput_mouse(int src) {
    int ufd = open("/dev/uinput", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (ufd < 0) return -1;

    setup_capabilities(src, ufd);

    struct uinput_user_dev dev;
    memset(&dev, 0, sizeof(dev));
    snprintf(dev.name, sizeof(dev.name), "m2-m4-macro-virtual-mouse");
    dev.id.bustype = BUS_USB;
    dev.id.vendor = 0xfeed;
    dev.id.product = 0x1004;
    dev.id.version = 1;

    if (write(ufd, &dev, sizeof(dev)) < 0) {
        close(ufd);
        return -1;
    }

    if (ioctl(ufd, UI_DEV_CREATE) < 0) {
        close(ufd);
        return -1;
    }

    sleep_ms(100);
    return ufd;
}

static bool emit_event(int fd, unsigned short type, unsigned short code, int value) {
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    return write(fd, &ev, sizeof(ev)) == sizeof(ev);
}

static void emit_syn(int fd) {
    emit_event(fd, EV_SYN, SYN_REPORT, 0);
}

static void emit_pair(int fd, int value) {
    emit_event(fd, EV_KEY, BTN_RIGHT, value);
    emit_event(fd, EV_KEY, BTN_SIDE, value);
    emit_syn(fd);
}

static void usage(const char *name) {
    fprintf(stderr, "usage: %s [/dev/input/eventN]\n", name);
}

int main(int argc, char **argv) {
    const char *env_flag = getenv("M1_M4_FLAG");
    if (env_flag && *env_flag) flag_path = env_flag;

    char device_path[256];
    if (argc > 2) {
        usage(argv[0]);
        return 2;
    }

    if (argc == 2) {
        snprintf(device_path, sizeof(device_path), "%s", argv[1]);
    } else if (find_mouse(device_path, sizeof(device_path)) < 0) {
        fprintf(stderr, "m1_m4_macro: mouse with BTN_RIGHT and BTN_SIDE not found\n");
        return 1;
    }

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    int src = open(device_path, O_RDONLY | O_CLOEXEC);
    if (src < 0) {
        fprintf(stderr, "m1_m4_macro: cannot open %s: %s\n", device_path, strerror(errno));
        return 1;
    }

    if (!looks_like_mouse(src) || !has_macro_button(src)) {
        fprintf(stderr, "m1_m4_macro: selected device is not a mouse with BTN_SIDE\n");
        close(src);
        return 1;
    }

    int ufd = create_uinput_mouse(src);
    if (ufd < 0) {
        fprintf(stderr, "m1_m4_macro: cannot create uinput device: %s\n", strerror(errno));
        close(src);
        return 1;
    }

    if (ioctl(src, EVIOCGRAB, 1) < 0) {
        fprintf(stderr, "m1_m4_macro: cannot grab %s: %s\n", device_path, strerror(errno));
        ioctl(ufd, UI_DEV_DESTROY);
        close(ufd);
        close(src);
        return 1;
    }

    pthread_t thread;
    if (pthread_create(&thread, NULL, state_thread, NULL) != 0) {
        ioctl(src, EVIOCGRAB, 0);
        ioctl(ufd, UI_DEV_DESTROY);
        close(ufd);
        close(src);
        return 1;
    }

    bool pair_down = false;
    bool physical_right = false;
    bool physical_side = false;
    bool pass_right_down = false;
    bool pass_side_down = false;
    bool was_allowed = false;

    while (atomic_load(&running)) {
        struct input_event ev;
        ssize_t n = read(src, &ev, sizeof(ev));
        if (n < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (n != sizeof(ev)) continue;

        bool allowed = atomic_load(&macro_allowed);
        if (allowed && !was_allowed) {
            bool released = false;
            if (pass_right_down) {
                emit_event(ufd, EV_KEY, BTN_RIGHT, 0);
                pass_right_down = false;
                released = true;
            }
            if (pass_side_down) {
                emit_event(ufd, EV_KEY, BTN_SIDE, 0);
                pass_side_down = false;
                released = true;
            }
            if (released) emit_syn(ufd);
        }
        if (!allowed && was_allowed && pair_down) {
            emit_pair(ufd, 0);
            pair_down = false;
        }
        was_allowed = allowed;

        if (ev.type == EV_KEY && (ev.code == BTN_RIGHT || ev.code == BTN_SIDE)) {
            bool pressed = ev.value != 0;
            if (ev.code == BTN_RIGHT) physical_right = pressed;
            if (ev.code == BTN_SIDE) physical_side = pressed;

            if (allowed) {
                bool desired = physical_right || physical_side;
                if (desired != pair_down) {
                    emit_pair(ufd, desired ? 1 : 0);
                    pair_down = desired;
                }
                continue;
            }

            if (ev.code == BTN_RIGHT) pass_right_down = pressed;
            if (ev.code == BTN_SIDE) pass_side_down = pressed;
        }

        write(ufd, &ev, sizeof(ev));
    }

    if (pair_down) emit_pair(ufd, 0);

    atomic_store(&running, false);
    pthread_join(thread, NULL);

    ioctl(src, EVIOCGRAB, 0);
    ioctl(ufd, UI_DEV_DESTROY);
    close(ufd);
    close(src);

    return 0;
}
