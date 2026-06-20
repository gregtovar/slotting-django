#!/bin/bash
# Starts, in order: a virtual X display -> the Tkinter app on it ->
# a password-protected VNC server bridging that display ->
# websockify/noVNC bridging VNC to plain HTTP so a browser can connect.
set -e

VNC_PASSWORD="${VNC_PASSWORD:?Set VNC_PASSWORD when starting the container (see docker-compose.yml)}"
SCREEN_GEOMETRY="${SCREEN_GEOMETRY:-1280x800x24}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

echo "[entrypoint] Starting Xvfb on $DISPLAY ($SCREEN_GEOMETRY)..."
Xvfb "$DISPLAY" -screen 0 "$SCREEN_GEOMETRY" -nolisten tcp &
XVFB_PID=$!

# Wait for the X socket to actually be ready instead of a fixed sleep
for i in $(seq 1 20); do
    if [ -e "/tmp/.X11-unix/X${DISPLAY#:}" ]; then
        break
    fi
    sleep 0.5
done

echo "[entrypoint] Launching Slotting Optimizer..."
cd /app/slotting_optimizer
python3 main.py &
APP_PID=$!

sleep 2
if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "[entrypoint] ERROR: the app exited immediately - check the logs above." >&2
    exit 1
fi

mkdir -p /root/.vnc
x11vnc -storepasswd "$VNC_PASSWORD" /root/.vnc/passwd >/dev/null

echo "[entrypoint] Starting x11vnc..."
x11vnc -display "$DISPLAY" -forever -shared -rfbauth /root/.vnc/passwd -rfbport 5900 -quiet &
VNC_PID=$!
sleep 1

echo "[entrypoint] Starting noVNC/websockify on port $NOVNC_PORT..."
websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:5900 &
WS_PID=$!

# If the app process dies (e.g. someone closes/quits it), bring the
# whole container down so an orchestrator (docker compose / systemd)
# can restart a clean session rather than leaving a blank screen up.
wait -n "$APP_PID" "$VNC_PID" "$WS_PID"
echo "[entrypoint] A child process exited - shutting down the session."
kill "$XVFB_PID" "$APP_PID" "$VNC_PID" "$WS_PID" 2>/dev/null || true
