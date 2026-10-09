#!/usr/bin/env bash
# serve a built site on 127.0.0.1:<port>, open it in Chromium on the rig desktop, save a full screenshot
NAME=$1; PORT=${2:-4173}; D=~/sitebench/$NAME
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$(ls /run/user/1000/hypr/ | head -1)
cd $D; [ -d dist ] || npm run build
setsid nohup npx vite preview --host 127.0.0.1 --port $PORT --strictPort > ~/sitebench/$NAME.run/preview.log 2>&1 < /dev/null &
for i in $(seq 30); do curl -sf http://127.0.0.1:$PORT >/dev/null && break; sleep 1; done
chromium --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 --screenshot=$HOME/sitebench/$NAME.run/top.png http://127.0.0.1:$PORT >/dev/null 2>&1
chromium --headless=new --disable-gpu --hide-scrollbars --window-size=1440,4200 --screenshot=$HOME/sitebench/$NAME.run/full.png http://127.0.0.1:$PORT >/dev/null 2>&1
setsid nohup chromium --new-window --user-data-dir=$HOME/.cache/sitebench-chrome http://127.0.0.1:$PORT >/dev/null 2>&1 < /dev/null &
echo served on $PORT
