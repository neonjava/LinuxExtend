#!/usr/bin/env bash
# Switch mouse cursor and monitor focus between primary monitor and virtual headless monitor

if ! command -v hyprctl >/dev/null 2>&1; then
    exit 0
fi

FOCUSED_MON=$(hyprctl monitors -j 2>/dev/null | jq -r '.[] | select(.focused) | .name')
HEADLESS_MON=$(hyprctl monitors -j 2>/dev/null | jq -r '.[] | select(.name | startswith("HEADLESS")) | .name' | head -1)
PRIMARY_MON=$(hyprctl monitors -j 2>/dev/null | jq -r '.[] | select((.name | startswith("HEADLESS") | not)) | .name' | head -1)

if [ -z "$HEADLESS_MON" ]; then
    # No virtual monitor active
    exit 0
fi

if [ "$FOCUSED_MON" = "$HEADLESS_MON" ]; then
    TARGET_MON="$PRIMARY_MON"
else
    TARGET_MON="$HEADLESS_MON"
fi

[ -z "$TARGET_MON" ] && exit 0

# Calculate center coordinates of target monitor
TARGET_INFO=$(hyprctl monitors -j 2>/dev/null | jq -r ".[] | select(.name == \"$TARGET_MON\")")
TARGET_X=$(echo "$TARGET_INFO" | jq -r '.x // 0')
TARGET_Y=$(echo "$TARGET_INFO" | jq -r '.y // 0')
TARGET_W=$(echo "$TARGET_INFO" | jq -r '.width // 1920')
TARGET_H=$(echo "$TARGET_INFO" | jq -r '.height // 1080')
TARGET_TRANSFORM=$(echo "$TARGET_INFO" | jq -r '.transform // 0')

# Account for rotated orientation
if [ "$TARGET_TRANSFORM" -eq 1 ] || [ "$TARGET_TRANSFORM" -eq 3 ]; then
    EFF_W=$TARGET_H
    EFF_H=$TARGET_W
else
    EFF_W=$TARGET_W
    EFF_H=$TARGET_H
fi

CENTER_X=$(( TARGET_X + EFF_W / 2 ))
CENTER_Y=$(( TARGET_Y + EFF_H / 2 ))

hyprctl dispatch focusmonitor "$TARGET_MON" >/dev/null 2>&1 || true
hyprctl dispatch movecursor "$CENTER_X" "$CENTER_Y" >/dev/null 2>&1 || true
