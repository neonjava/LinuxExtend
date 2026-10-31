#!/usr/bin/env bash
#
# linuxextend - Control LinuxExtend virtual tablet monitor
#

set -eo pipefail

INSTALL_DIR="/home/neonjava/LinuxExtend"
LOG_DIR="$HOME/.local/state/linuxextend"
LOG_FILE="$LOG_DIR/server.log"
PID_FILE="$LOG_DIR/server.pid"
ADB_BIN="/home/neonjava/Android/Sdk/platform-tools/adb"
[ -x "$ADB_BIN" ] || ADB_BIN="$(command -v adb 2>/dev/null || true)"

mkdir -p "$LOG_DIR"

# Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_BLUE="\033[34m"
C_CYAN="\033[36m"
C_YELLOW="\033[33m"
C_RED="\033[31m"

is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    # Fallback to pgrep
    pgrep -f "python3 -m linuxextend" >/dev/null 2>&1
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return
        fi
    fi
    pgrep -f "python3 -m linuxextend" | head -1
}

cleanup_displays() {
    # Remove any stray HEADLESS monitors from Hyprland
    if command -v hyprctl >/dev/null 2>&1; then
        local headless_monitors
        headless_monitors=$(hyprctl monitors -j 2>/dev/null | jq -r '.[] | select(.name | startswith("HEADLESS")) | .name' 2>/dev/null || true)
        for mon in $headless_monitors; do
            echo -e "  ${C_YELLOW}Removing Hyprland output ${mon}...${C_RESET}"
            hyprctl output remove "$mon" >/dev/null 2>&1 || true
        done
    fi
}

setup_usb() {
    if [ -n "$ADB_BIN" ] && [ -x "$ADB_BIN" ]; then
        local device_count
        device_count=$("$ADB_BIN" devices 2>/dev/null | grep -v "List" | grep -c "device$" || true)
        if [ "$device_count" -gt 0 ]; then
            echo -e "  ${C_CYAN}Setting up ADB reverse port forwarding (8080)...${C_RESET}"
            "$ADB_BIN" reverse tcp:8080 tcp:8080 >/dev/null 2>&1 || true
            echo -e "  ${C_GREEN}✓ USB ADB reverse active${C_RESET}"
            
            # Check if app is installed and launch it
            if "$ADB_BIN" shell pm list packages 2>/dev/null | grep -q "com.linuxextend"; then
                echo -e "  ${C_CYAN}Launching LinuxExtend on tablet...${C_RESET}"
                "$ADB_BIN" shell am start -n com.linuxextend/.MainActivity >/dev/null 2>&1 || true
            fi
        fi
    fi
}

cmd_start() {
    if is_running; then
        local pid
        pid=$(get_pid)
        echo -e "${C_YELLOW}LinuxExtend is already running (PID: ${pid}).${C_RESET}"
        cmd_status
        return 0
    fi

    # Clean up any leftover displays first
    cleanup_displays

    echo -e "${C_BOLD}${C_BLUE}Starting LinuxExtend server...${C_RESET}"
    cd "$INSTALL_DIR/server"

    # Start server in background
    nohup python3 -m linuxextend "$@" > "$LOG_FILE" 2>&1 &
    local s_pid=$!
    echo "$s_pid" > "$PID_FILE"

    # Wait for virtual display initialization
    local timeout=10
    local elapsed=0
    echo -n "  Waiting for virtual monitor initialization..."
    while [ $elapsed -lt $timeout ]; do
        if hyprctl monitors 2>/dev/null | grep -q "HEADLESS"; then
            echo -e " ${C_GREEN}done!${C_RESET}"
            break
        fi
        if ! kill -0 "$s_pid" 2>/dev/null; then
            echo -e " ${C_RED}failed to start!${C_RESET}"
            echo -e "${C_RED}Server log:${C_RESET}"
            tail -n 15 "$LOG_FILE"
            rm -f "$PID_FILE"
            return 1
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
        echo -n "."
    done

    # Setup USB port forwarding if tablet is plugged in
    setup_usb

    local host_ip
    host_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || echo "127.0.0.1")

    echo ""
    echo -e "${C_BOLD}${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
    echo -e "${C_BOLD} 🖥️  LinuxExtend is ACTIVE!${C_RESET}"
    echo -e "  PID:      ${s_pid}"
    echo -e "  Display:  $(hyprctl monitors 2>/dev/null | grep -o 'HEADLESS-[0-9]*' | head -1 || echo 'HEADLESS')"
    echo -e "  Wi-Fi:    ${C_CYAN}http://${host_ip}:8080/${C_RESET}"
    echo -e "  USB:      ${C_CYAN}http://127.0.0.1:8080/${C_RESET} (or LinuxExtend App)"
    echo -e ""
    echo -e "  Keybindings:"
    echo -e "   • ${C_YELLOW}SHIFT + TAB${C_RESET} : Jump cursor between laptop & tablet"
    echo -e "   • ${C_YELLOW}SUPER + M${C_RESET}   : Throw active window to tablet"
    echo -e "${C_BOLD}${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
    echo ""
}

cmd_stop() {
    echo -e "${C_BOLD}${C_BLUE}Stopping LinuxExtend...${C_RESET}"
    local stopped=0

    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo -e "  ${C_YELLOW}Stopping server process (PID: ${pid})...${C_RESET}"
        kill -15 "$pid" 2>/dev/null || true
        
        # Wait up to 3 seconds for graceful shutdown
        for _ in {1..30}; do
            if ! kill -0 "$pid" 2>/dev/null; then
                stopped=1
                break
            fi
            sleep 0.1
        done

        if [ "$stopped" -eq 0 ]; then
            echo -e "  ${C_RED}Force killing server...${C_RESET}"
            kill -9 "$pid" 2>/dev/null || true
        fi
    else
        echo -e "  ${C_DIM}No server process found.${C_RESET}"
    fi

    # Kill any remaining instances
    pkill -f "python3 -m linuxextend" 2>/dev/null || true
    rm -f "$PID_FILE"

    # Clean up virtual monitors from Hyprland
    cleanup_displays

    # Clean up ADB reverse port
    if [ -n "$ADB_BIN" ] && [ -x "$ADB_BIN" ]; then
        "$ADB_BIN" reverse --remove tcp:8080 >/dev/null 2>&1 || true
        # Close app on tablet
        "$ADB_BIN" shell am force-stop com.linuxextend >/dev/null 2>&1 || true
    fi

    echo -e "${C_GREEN}✓ LinuxExtend stopped and display cleaned up.${C_RESET}"
}

cmd_status() {
    echo -e "${C_BOLD}LinuxExtend Status:${C_RESET}"
    if is_running; then
        local pid
        pid=$(get_pid)
        echo -e "  Server:   ${C_GREEN}● Running${C_RESET} (PID: ${pid})"
        local host_ip
        host_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || echo "127.0.0.1")
        echo -e "  Endpoint: http://${host_ip}:8080/"
    else
        echo -e "  Server:   ${C_RED}○ Stopped${C_RESET}"
    fi

    # Hyprland monitor status
    local headless
    headless=$(hyprctl monitors 2>/dev/null | grep -A 2 -B 1 "HEADLESS" || true)
    if [ -n "$headless" ]; then
        echo -e "  Display:  ${C_GREEN}● Active${C_RESET}"
        echo "$headless" | sed 's/^/    /'
    else
        echo -e "  Display:  ${C_RED}○ None${C_RESET}"
    fi

    # Tablet USB status
    if [ -n "$ADB_BIN" ] && [ -x "$ADB_BIN" ]; then
        local dev
        dev=$("$ADB_BIN" devices 2>/dev/null | grep -v "List" | grep "device$" | awk '{print $1}' || true)
        if [ -n "$dev" ]; then
            echo -e "  Tablet:   ${C_GREEN}● Connected via USB${C_RESET} (${dev})"
        else
            echo -e "  Tablet:   ${C_YELLOW}○ No USB device connected${C_RESET}"
        fi
    fi
}

cmd_usb() {
    echo -e "${C_BOLD}Setting up USB Mode for Tablet...${C_RESET}"
    setup_usb
}

cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

cmd_switch() {
    if [ -f "$INSTALL_DIR/scripts/switch_monitor.sh" ]; then
        "$INSTALL_DIR/scripts/switch_monitor.sh"
    fi
}

case "${1:-}" in
    start|on|enable|run)
        shift || true
        cmd_start "$@"
        ;;
    stop|off|disable|kill)
        cmd_stop
        ;;
    restart)
        cmd_stop
        sleep 1
        shift || true
        cmd_start "$@"
        ;;
    status)
        cmd_status
        ;;
    usb)
        cmd_usb
        ;;
    logs|log)
        cmd_logs
        ;;
    switch)
        cmd_switch
        ;;
    *)
        echo -e "${C_BOLD}Usage:${C_RESET} linuxextend <command>"
        echo ""
        echo -e "  ${C_GREEN}start${C_RESET} | ${C_GREEN}on${C_RESET}     Start second monitor server and configure tablet"
        echo -e "  ${C_RED}stop${C_RESET}  | ${C_RED}off${C_RESET}    Stop server, clean up socket & remove virtual display"
        echo -e "  ${C_CYAN}status${C_RESET}        Show server, monitor, and tablet connection status"
        echo -e "  ${C_YELLOW}restart${C_RESET}       Restart LinuxExtend server"
        echo -e "  ${C_BLUE}usb${C_RESET}           Re-apply USB port forwarding & launch app on tablet"
        echo -e "  ${C_BLUE}logs${C_RESET}          Follow server logs in real time"
        echo -e "  ${C_BLUE}switch${C_RESET}        Jump mouse cursor between laptop & tablet"
        echo ""
        ;;
esac
