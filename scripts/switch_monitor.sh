#!/usr/bin/env bash
# Switch mouse cursor and monitor focus between laptop (eDP-1) and tablet (HEADLESS-*)

CURSOR_POS=$(hyprctl cursorpos | tr -d ' ')
CURSOR_X=$(echo "$CURSOR_POS" | cut -d',' -f1)

# Laptop width is 1920
if [ "${CURSOR_X:-0}" -lt 1920 ]; then
    # Currently on Laptop -> Jump to Tablet (centered at 2880, 540)
    hyprctl dispatch movecursor 2880 540
    HEADLESS_NAME=$(hyprctl monitors -j | jq -r '.[] | select(.name | startswith("HEADLESS")) | .name' | head -1)
    if [ -n "$HEADLESS_NAME" ]; then
        hyprctl dispatch focusmonitor "$HEADLESS_NAME"
    fi
else
    # Currently on Tablet -> Jump to Laptop (centered at 960, 540)
    hyprctl dispatch movecursor 960 540
    hyprctl dispatch focusmonitor eDP-1
fi
