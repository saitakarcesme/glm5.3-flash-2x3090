#!/usr/bin/env bash
# open a desktop window that runs one session and shows it live
NAME=$1; PROMPT=$2
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$(ls /run/user/1000/hypr/ | head -1)
mkdir -p ~/sitebench/$NAME.run; : > ~/sitebench/$NAME.run/session.jsonl
setsid nohup ~/sitebench/run_site.sh "$NAME" "$PROMPT" > ~/sitebench/$NAME.run/runner.out 2>&1 < /dev/null &
setsid nohup foot --title="GLM session — $NAME" bash -c "printf \"\e[1;33mGLM-5.3-Flash (ours, 2x3090) — $NAME\e[0m\n\n\"; python3 ~/sitebench/live.py ~/sitebench/$NAME.run/session.jsonl; exec bash" >/dev/null 2>&1 < /dev/null &
