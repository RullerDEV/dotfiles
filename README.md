# dotfiles

Hyprland clean glass rice — off-white `#f4f1ea`, blur sutil, Waybar compacta no topo, settings por Rofi e gamemode minimo/performance. Fonte Maple Mono NF, gerenciado com GNU Stow.

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
| **settings.sh** | app local de ajustes via Rofi |

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
4. Define tema inicial (light/off-white), perfil clean e recarrega serviços

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

## settings

Abra pela engrenagem da Waybar ou pelo terminal:

```sh
~/.config/hypr/scripts/settings.sh menu
```

Perfis:

| perfil | uso |
|---|---|
| `clean` | off-white glass padrao |
| `glass` | mais blur/transparencia |
| `focus` | bonito, mas menos distracao |
| `solid` | quase sem transparencia |

O settings app tambem alterna tema, gamemode, wallpaper, resolucao do `DP-1`, restart da Waybar e reload do Hyprland.

O `SUPER + G` ativa o gamemode: esconde Waybar, liga DND, remove blur/animacao/sombras/gaps/bordas, deixa opacidade solida e aplica ajustes de render/VRR. Desativar recarrega o perfil clean atual.

## paleta

| | dark | light |
|---|---|---|
| bg | `#0f1110` | `#f4f1ea` |
| surface | `#171a18` | `#fbfaf6` |
| border | `#353a34` | `#d5ccbf` |
| muted | `#8f9688` | `#7d766d` |
| fg | `#e9e4d8` | `#24231f` |
| accent | `#f4f1ea` | `#2d3530` |

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

- **Tema/perfis**: use a engrenagem da Waybar ou `rice` no fish
- **Wallpapers**: jogue imagens em `~/Pictures/Wallpapers/` e `SUPER+W` cicla
- **Keybinds**: `~/.config/hypr/hyprland.conf` (seção de `bind`)

## licença

MIT
