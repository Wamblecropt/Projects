#!/usr/bin/env bash

# Colors
RESET='\033[0m'
BOLD='\033[1m'
BLUE='\033[0;34m'

# Fedora ASCII Logo (from Neofetch)
logo_fedora=$(cat << 'EOF'
             .',;::::;,'.
         .';:cccccccccccc:;,.
      .;cccccccccccccccccccccc;.
    .:cccccccccccccccccccccccccc:.
  .;ccccccccccccc;.:dddl:.;ccccccc;.
 .:ccccccccccccc;OWMKOOXMWd;ccccccc:.
.:ccccccccccccc;KMMc;cc;xMMc;ccccccc:.
,cccccccccccccc;MMM.;cc;;WW:;cccccccc,
:cccccccccccccc;MMM.;cccccccccccccccc:
:ccccccc;ox0OOOo;MMM0OOk.;ccccccccccc:
cccccc;0MMKxdd:;MMMkddc.;cccccccccccc;
ccccc;XMO';cccc;MMM.;cccccccccccccccc'
ccccc;MMo;ccccc;MMW.;ccccccccccccccc;
ccccc;0MNc.ccc.xMMd.;cccccccccccccc;
cccccc;dNMWXXXWM0:;cccccccccccccc:,
cccccccc;.:odl:.ccccccccccccccc:,.
:ccccccccccccccccccccccccccccc'.
.:ccccccccccccccccccccccc:;,..
  '::ccccccccccccccc::;,.

EOF
)

# Get info
USER_HOST="${USER}@$(hostname)"
OS=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
KERNEL=$(uname -r)
UPTIME=$(uptime -p | sed 's/up //')
SHELL=$(basename "$SHELL")
CPU=$(lscpu | grep "Model name" | awk -F: '{print $2}' | sed 's/^ //')
CORES=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
RAM=$(free -h | awk '/Mem:/ {print $3 " / " $2}')
GPU=$(lspci | grep -i 'vga\|3d' | cut -d ':' -f3 | sed 's/^ //')
DE="${XDG_CURRENT_DESKTOP:-unknown}"
WM="${XDG_SESSION_DESKTOP:-unknown}"
RES=$(xdpyinfo 2>/dev/null | awk '/dimensions/{print $2}')
TERM=$(basename "$TERM")
PACKAGES=$(rpm -qa | wc -l)

# Color bars like Neofetch
function color_bars {
    echo
    echo -en "   "
    for code in {0..7}; do
        echo -en "\033[4${code}m    \033[0m"
    done
    echo
    echo -en "   "
    for code in {0..7}; do
        echo -en "\033[10${code}m    \033[0m"
    done
    echo -e "\n"
}

# Print with alignment
echo -e "${BLUE}${logo_fedora}${RESET}" | paste -d'\t' - <(
cat <<EOF
${BOLD}${USER_HOST}${RESET}
OS:           $OS
Kernel:       $KERNEL
Uptime:       $UPTIME
Shell:        $SHELL
CPU:          $CPU ($CORES cores)
GPU:          $GPU
RAM:          $RAM
DE:           $DE
WM:           $WM
Resolution:   ${RES:-unknown}
Terminal:     $TERM
Packages:     $PACKAGES
EOF
)

color_bars
