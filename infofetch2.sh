#!/usr/bin/env bash

# Colors
RESET="\033[0m"
ORANGE="\033[38;5;208m"   # orange for draogn and labels
VALUE="\033[1;37m"    # white values

# Dragon ASCII Logo
logo_dragon=$(cat <<'EOF'
                  __====-_   _-====___
            _--^^^#####//      \\#####^^^--_
         _-^##########// (    ) \\##########^-_
        -############//  |\^^/|  \\############-
      _/############//   (@::@)   \\############\_
     /#############((     \\//     ))#############\
    -###############\\    (oo)    //###############-
   -#################\\  / "" \  //#################-
  -###################\\/  (_)  \//###################-
 _#/|##########/\######(   "/"   )######/\##########|\#_
 |/ |#/\#/\#/\/  \#/\##\  ! ' !  /##/\#/  \/\#/\#/\#| \|
 `  |/  V  V '   V  \#\|  \ | /  |/#/  V   '  V  V  \|  '
    `   `  `      `   / | | | | | \   '      '  '   '
                     (  | | | | |  )
                    __\ | | | | | /__
                   (vvv(VVV)(VVV)vvv)
EOF
)

# System info
USER_HOST="${USER}@$(hostname)"
OS=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
KERNEL=$(uname -r)
UPTIME=$(uptime -p | sed 's/up //')
SHELL=$(basename "$SHELL")
CPU=$(lscpu | grep "Model name" | awk -F: '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
CORES=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
RAM=$(free -h | awk '/Mem:/ {print $3 " / " $2}')
GPU=$(lspci | grep -i 'vga\|3d' | cut -d ':' -f3 | sed 's/^ //')
DE="${XDG_CURRENT_DESKTOP:-unknown}"
WM="${XDG_SESSION_DESKTOP:-unknown}"
RES=$(xdpyinfo 2>/dev/null | awk '/dimensions/{print $2}')
TERM=$(basename "$TERM")
PACKAGES=$(dpkg --get-selections | grep -v deinstall | wc -l)

# Info lines
info_lines=(
  "$USER_HOST"
  "OS:           $OS"
  "Kernel:       $KERNEL"
  "Uptime:       $UPTIME"
  "Shell:        $SHELL"
  "CPU:          $CPU ($CORES cores)"
  "GPU:          $GPU"
  "RAM:          $RAM"
  "DE:           $DE"
  "WM:           $WM"
  "Resolution:   ${RES:-unknown}"
  "Terminal:     $TERM"
  "Packages:     $PACKAGES"
)

# Pad info_lines to match logo_lines length
while [ ${#info_lines[@]} -lt ${#logo_lines[@]} ]; do
    info_lines+=("")
done

# Determine max lines
max_logo_lines=${#logo_lines[@]}
max_info_lines=${#info_lines[@]}
max_lines=$(( max_logo_lines > max_info_lines ? max_logo_lines : max_info_lines ))

# Split logo into lines
IFS=$'\n' read -r -d '' -a logo_lines <<< "$logo_dragon"

# Print side by side
for i in "${!logo_lines[@]}"; do
    logo_line="${logo_lines[i]}"
    info="${info_lines[i]:-}"

    if [[ $i -eq 0 ]]; then
        # First line: username in orange
        printf "%-60s  ${ORANGE}%s${RESET}\n" "$logo_line" "$info"
    elif [[ "$info" =~ ":" ]]; then
        label="${info%%:*}:"
        value="${info#*: }"
        printf "%-60s  ${ORANGE}%s ${VALUE}%s${RESET}\n" "$logo_line" "$label" "$value"
    else
        printf "%-60s  %s\n" "$logo_line" "$info"
    fi
done
#---