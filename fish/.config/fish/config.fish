if status is-interactive
    set -gx EDITOR micro
    set -gx VISUAL micro
    set -gx PAGER less
    set -gx LESS "-R --use-color"
    set -gx MANPAGER "less -R --use-color -Dd+r -Du+b"

    set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
    set -gx FZF_DEFAULT_OPTS '--height 40% --reverse --border --color=bw'

    if test -f /usr/share/cachyos-fish-config/cachyos-config.fish
        source /usr/share/cachyos-fish-config/cachyos-config.fish
    end

    if type -q zoxide
        zoxide init fish | source
    end
end

abbr -a g     git
abbr -a gs    git status
abbr -a ga    git add
abbr -a gc    git commit
abbr -a gp    git push
abbr -a gl    git pull
abbr -a glg   git log --oneline --graph --decorate --all
abbr -a gd    git diff
abbr -a gco   git checkout

abbr -a dot   'cd ~/dotfiles'
abbr -a hyprr 'hyprctl reload'
abbr -a wbr   'pkill -SIGUSR2 waybar'
abbr -a tt    '~/.config/hypr/scripts/theme-toggle.sh'

abbr -a ll    'eza -la --icons --group-directories-first'
abbr -a la    'eza -a --icons'
abbr -a lt    'eza --tree --icons -L 2'
abbr -a cat   'bat --paging=never'

function fish_greeting
end
