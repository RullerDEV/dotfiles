#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$HOME/dotfiles}"
BACKUP_DIR="$HOME/.config-backup-$(date +%Y%m%d-%H%M%S)"

PACKAGES=(hypr waybar rofi kitty yazi swaync wlogout fish git)

DEPS=(stow swww waybar kitty rofi swaync wlogout hyprlock yazi grim slurp wl-clipboard cliphist brightnessctl jq fd ripgrep fzf zoxide ffmpegthumbnailer poppler unarchiver swappy)
FONTS=(maplemono-nf)

bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
warn()  { printf "\033[33m%s\033[0m\n" "$*"; }
ok()    { printf "\033[32m%s\033[0m\n" "$*"; }
err()   { printf "\033[31m%s\033[0m\n" "$*" >&2; }

cd "$DOTFILES_DIR"

bold "==> dotfiles em $DOTFILES_DIR"

if ! command -v stow >/dev/null 2>&1; then
    err "stow nao encontrado. instale: sudo pacman -S stow"
    exit 1
fi

bold "==> verificando dependencias"
missing=()
for d in "${DEPS[@]}" "${FONTS[@]}"; do
    if ! pacman -Q "$d" >/dev/null 2>&1; then
        missing+=("$d")
    fi
done

if [ "${#missing[@]}" -gt 0 ]; then
    warn "faltando: ${missing[*]}"
    if command -v yay >/dev/null 2>&1; then
        bold "==> instalando via yay"
        yay -S --needed --noconfirm "${missing[@]}" || warn "alguns pacotes podem ter falhado"
    else
        warn "instale manualmente: yay -S ${missing[*]}"
    fi
else
    ok "todas as dependencias presentes"
fi

bold "==> backup das configs atuais em $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
for sub in hypr waybar rofi kitty yazi swaync wlogout wofi mako fish; do
    if [ -d "$HOME/.config/$sub" ] && [ ! -L "$HOME/.config/$sub" ]; then
        cp -r "$HOME/.config/$sub" "$BACKUP_DIR/" 2>/dev/null || true
    fi
done
[ -f "$HOME/.gitconfig" ] && [ ! -L "$HOME/.gitconfig" ] && cp "$HOME/.gitconfig" "$BACKUP_DIR/gitconfig" 2>/dev/null || true
ok "backup salvo em $BACKUP_DIR"

bold "==> aplicando stow"
for pkg in "${PACKAGES[@]}"; do
    stow --restow --target="$HOME" "$pkg"
    ok "stow $pkg"
done

bold "==> definindo tema inicial (dark)"
mkdir -p "$HOME/.cache"
echo -n dark > "$HOME/.cache/theme"
ln -sfn "$HOME/.config/hypr/themes/dark.conf"      "$HOME/.config/hypr/themes/current.conf"
ln -sfn "$HOME/.config/waybar/themes/dark.css"     "$HOME/.config/waybar/themes/current.css"
ln -sfn "$HOME/.config/kitty/themes/dark.conf"     "$HOME/.config/kitty/themes/current.conf"
ln -sfn "$HOME/.config/rofi/themes/mono-dark.rasi" "$HOME/.config/rofi/themes/current.rasi"
ln -sfn "$HOME/.config/yazi/themes/mono-dark.toml" "$HOME/.config/yazi/themes/current.toml"

bold "==> recarregando servicos"
if pgrep -x mako >/dev/null 2>&1; then
    pkill -x mako 2>/dev/null || true
fi
if command -v hyprctl >/dev/null 2>&1; then
    hyprctl reload >/dev/null 2>&1 || true
fi
if pgrep -x waybar >/dev/null 2>&1; then
    pkill -x waybar; sleep 0.3; nohup waybar >/dev/null 2>&1 &
elif command -v waybar >/dev/null 2>&1; then
    nohup waybar >/dev/null 2>&1 &
fi
if ! pgrep -x swaync >/dev/null 2>&1 && command -v swaync >/dev/null 2>&1; then
    nohup swaync >/dev/null 2>&1 &
fi

ok "==> instalado. atalhos: SUPER+R (rofi), SUPER+T (toggle), SUPER+E (yazi), SUPER+SHIFT+L (lock), SUPER+SHIFT+E (logout)"
