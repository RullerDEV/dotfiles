#!/usr/bin/env bash
set -euo pipefail

WALL_DIR="${WALL_DIR:-$HOME/Pictures/Wallpapers}"
STATE="${XDG_CACHE_HOME:-$HOME/.cache}/wallpaper"
TRANS_TYPE="${TRANS_TYPE:-grow}"
TRANS_DUR="${TRANS_DUR:-1.2}"

mkdir -p "$WALL_DIR" "$(dirname "$STATE")"

if command -v swww >/dev/null 2>&1; then
    WALL_CMD="swww"
    WALL_DAEMON="swww-daemon"
elif command -v awww >/dev/null 2>&1; then
    WALL_CMD="awww"
    WALL_DAEMON="awww-daemon"
else
    echo "neither swww nor awww is installed" >&2
    exit 1
fi

if ! pgrep -x "$WALL_DAEMON" >/dev/null 2>&1; then
    "$WALL_DAEMON" >/dev/null 2>&1 &
    sleep 0.4
fi

mapfile -t walls < <(
    find "$WALL_DIR" -maxdepth 2 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) -print0 |
    while IFS= read -r -d '' candidate; do
        mime="$(file --brief --mime-type "$candidate" 2>/dev/null || true)"
        case "$mime" in
            image/jpeg|image/png|image/webp)
                printf '%s\n' "$candidate"
                ;;
        esac
    done | sort
)
mapfile -t monitors < <(hyprctl monitors -j | jq -r '.[].name')

if [ "${#walls[@]}" -eq 0 ]; then
    exit 0
fi

if [ "${#monitors[@]}" -eq 0 ]; then
    echo "no monitors found" >&2
    exit 1
fi

if [ "${#walls[@]}" -lt "${#monitors[@]}" ]; then
    echo "need at least ${#monitors[@]} wallpapers for ${#monitors[@]} monitors" >&2
    exit 1
fi

focused_monitor="$(hyprctl monitors -j | jq -r '.[] | select(.focused == true) | .name' | head -n1)"

wall_index() {
    local needle="$1"
    local i
    for i in "${!walls[@]}"; do
        if [ "${walls[$i]}" = "$needle" ]; then
            printf '%s\n' "$i"
            return 0
        fi
    done
    return 1
}

read_state() {
    declare -gA current_map=()
    if [ ! -s "$STATE" ]; then
        return 0
    fi

    while IFS='|' read -r mon img; do
        [ -n "${mon:-}" ] || continue
        [ -n "${img:-}" ] || continue
        current_map["$mon"]="$img"
    done < "$STATE"
}

write_state() {
    : > "$STATE"
    local mon
    for mon in "${monitors[@]}"; do
        printf '%s|%s\n' "$mon" "${next_map[$mon]}" >> "$STATE"
    done
}

apply_wall() {
    local mon="$1"
    local img="$2"
    "$WALL_CMD" img "$img" --outputs "$mon" --transition-type "$TRANS_TYPE" --transition-duration "$TRANS_DUR" --transition-fps 60
}

declare -A used
declare -A next_map

assign_unique_random() {
    local tries=0
    local mon idx candidate changed valid

    while [ "$tries" -lt 50 ]; do
        used=()
        next_map=()
        valid=1
        changed=0

        for mon in "${monitors[@]}"; do
            local pool=()
            for candidate in "${walls[@]}"; do
                [ -z "${used[$candidate]+x}" ] || continue
                pool+=("$candidate")
            done

            if [ "${#pool[@]}" -eq 0 ]; then
                valid=0
                break
            fi

            candidate="${pool[$(( RANDOM % ${#pool[@]} ))]}"
            next_map["$mon"]="$candidate"
            used["$candidate"]=1

            if [ "${current_map[$mon]:-}" != "$candidate" ]; then
                changed=1
            fi
        done

        if [ "$valid" -eq 1 ] && [ "$changed" -eq 1 ]; then
            return 0
        fi

        tries=$((tries + 1))
    done

    return 1
}

assign_from_rotation() {
    local direction="${1:-next}"
    local shift=1
    local offset=0
    local i mon base_idx target_idx candidate unique

    if [ "$direction" = "prev" ]; then
        shift=$(( ${#walls[@]} - 1 ))
    fi

    for offset in $(seq 1 "${#walls[@]}"); do
        used=()
        next_map=()
        unique=1

        for i in "${!monitors[@]}"; do
            mon="${monitors[$i]}"
            if [ -n "${current_map[$mon]:-}" ] && base_idx="$(wall_index "${current_map[$mon]}")"; then
                :
            else
                base_idx="$i"
            fi
            target_idx=$(( (base_idx + offset * shift) % ${#walls[@]} ))
            candidate="${walls[$target_idx]}"

            if [ -n "${used[$candidate]+x}" ]; then
                unique=0
                break
            fi

            next_map["$mon"]="$candidate"
            used["$candidate"]=1
        done

        if [ "$unique" -eq 1 ]; then
            return 0
        fi
    done

    return 1
}

assign_with_selected() {
    local selected="$1"
    local selected_monitor="${focused_monitor:-${monitors[0]}}"
    local mon candidate

    used=()
    next_map=()
    next_map["$selected_monitor"]="$selected"
    used["$selected"]=1

    for mon in "${monitors[@]}"; do
        [ "$mon" = "$selected_monitor" ] && continue

        candidate=""
        for candidate in "${walls[@]}"; do
            [ "$candidate" = "$selected" ] && continue
            [ -z "${used[$candidate]+x}" ] || continue
            if [ "${current_map[$mon]:-}" != "$candidate" ]; then
                break
            fi
        done

        if [ -z "$candidate" ] || [ -n "${used[$candidate]+x}" ]; then
            for candidate in "${walls[@]}"; do
                [ "$candidate" = "$selected" ] && continue
                [ -z "${used[$candidate]+x}" ] || continue
                break
            done
        fi

        if [ -z "$candidate" ] || [ -n "${used[$candidate]+x}" ]; then
            echo "unable to assign unique wallpapers to all monitors" >&2
            exit 1
        fi

        next_map["$mon"]="$candidate"
        used["$candidate"]=1
    done
}

restore_or_generate() {
    local mon seen_img=0
    declare -A seen=()

    if [ -s "$STATE" ]; then
        for mon in "${monitors[@]}"; do
            local img="${current_map[$mon]:-}"
            [ -n "$img" ] || return 1
            [ -f "$img" ] || return 1
            [ -z "${seen[$img]+x}" ] || return 1
            seen["$img"]=1
            next_map["$mon"]="$img"
            seen_img=1
        done
    fi

    [ "$seen_img" -eq 1 ]
}

read_state

cmd="${1:-init}"
case "$cmd" in
    init)
        if ! restore_or_generate; then
            assign_unique_random || {
                echo "unable to generate unique wallpapers" >&2
                exit 1
            }
        fi
        ;;
    next)
        assign_from_rotation next || assign_unique_random || {
            echo "unable to generate next unique wallpapers" >&2
            exit 1
        }
        ;;
    prev)
        assign_from_rotation prev || assign_unique_random || {
            echo "unable to generate previous unique wallpapers" >&2
            exit 1
        }
        ;;
    random)
        assign_unique_random || {
            echo "unable to generate random unique wallpapers" >&2
            exit 1
        }
        ;;
    set)
        img="${2:-}"
        if [ -z "$img" ] || [ ! -f "$img" ]; then
            echo "usage: $0 set <image>" >&2
            exit 2
        fi
        assign_with_selected "$img"
        ;;
    *)
        echo "usage: $0 [init|next|prev|random|set <image>]" >&2
        exit 2
        ;;
esac

for mon in "${monitors[@]}"; do
    apply_wall "$mon" "${next_map[$mon]}"
done

write_state
