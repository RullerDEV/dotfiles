# dotfiles

Hyprland mono rice — off-black `#0a0a0a` / off-white `#f5f5f5`, toggle dark/light por keybind, fonte Maple Mono NF, gerenciado com GNU Stow.

![preview](preview.png)

## stack

| componente | uso |
|---|---|
| **Hyprland** | window manager (Wayland, NVIDIA) |
| **Waybar** | status bar floating no topo |
| **Rofi (rofi-wayland)** | launcher (drun, run, window) |
| **Kitty** | terminal emulator |
| **Yazi** | file manager TUI com previews |
| **swaync** | notification daemon + control center |
| **wlogout** | menu de power |
| **Hyprlock** | lockscreen |
| **swww** | wallpaper engine animado |
| **Fish** | shell |

## instalação

```sh
git clone https://github.com/lipedev/dotfiles.git ~/dotfiles
cd ~/dotfiles
./install.sh
```

O `install.sh`:
1. Verifica dependências e instala via `yay` se faltar
2. Faz backup das configs atuais em `~/.config-backup-AAAAMMDD/`
3. Aplica `stow` pra cada pacote
4. Define tema inicial (dark) e recarrega serviços

## keybinds principais

| atalho | ação |
|---|---|
| `SUPER + Enter` | terminal (kitty) |
| `SUPER + R` | launcher (rofi) |
| `SUPER + E` | file manager (yazi) |
| `SUPER + B` | browser (brave) |
| `SUPER + Q` | fechar janela |
| `SUPER + V` | toggle floating |
| `SUPER + F` | fullscreen |
| `SUPER + T` | toggle dark/light |
| `SUPER + G` | toggle gamemode |
| `SUPER + W` | próximo wallpaper |
| `SUPER + SHIFT + L` | lock (hyprlock) |
| `SUPER + SHIFT + E` | power menu (wlogout) |
| `SUPER + SHIFT + S` / `Print` | screenshot área |
| `SHIFT + Print` | screenshot full |
| `SUPER + Print` | screenshot janela ativa |
| `SUPER + SHIFT + V` | clipboard (cliphist) |
| `SUPER + SHIFT + N` | toggle notification panel |
| `SUPER + h/j/k/l` | mover foco (vim-like) |
| `SUPER + SHIFT + h/j/k/l` | mover janela |
| `SUPER + CTRL + setas` | redimensionar |
| `SUPER + 1-9` | workspace |
| `SUPER + SHIFT + 1-9` | mover janela pro workspace |

## paleta

| | dark | light |
|---|---|---|
| bg | `#0a0a0a` | `#f5f5f5` |
| surface | `#141414` | `#ebebeb` |
| border | `#2a2a2a` | `#c8c8c8` |
| muted | `#6e6e6e` | `#8a8a8a` |
| fg | `#e8e8e8` | `#1a1a1a` |
| accent | `#fafafa` | `#0a0a0a` |

## estrutura

```
~/dotfiles/
├── install.sh
├── hypr/      → ~/.config/hypr/
├── waybar/    → ~/.config/waybar/
├── rofi/      → ~/.config/rofi/
├── kitty/     → ~/.config/kitty/
├── yazi/      → ~/.config/yazi/
├── swaync/    → ~/.config/swaync/
├── wlogout/   → ~/.config/wlogout/
├── fish/      → ~/.config/fish/
└── git/       → ~/.gitconfig
```

Cada subpasta é um pacote `stow`. O comando `stow -t ~ <pkg>` cria os symlinks.

## customizar

- **Tema**: edite `*/themes/{dark,light}.*` e rode `SUPER+T`
- **Wallpapers**: jogue imagens em `~/Pictures/Wallpapers/` e `SUPER+W` cicla
- **Keybinds**: `~/.config/hypr/hyprland.conf` (seção de `bind`)

## licença

MIT
