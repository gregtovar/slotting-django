# Slotting Optimizer - remote-access image
# -----------------------------------------
# Runs the existing, unmodified Tkinter app against a virtual X display
# (Xvfb), bridges it out over VNC (x11vnc), then bridges VNC to plain
# HTTP/WebSocket (websockify + noVNC) so anyone can open it in a browser
# tab - no VNC client, no X server, nothing to install on their end.
#
# Each container is ONE independent session. Run two containers (see
# docker-compose.yml) to give two people their own separate sessions.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-tk \
        xvfb \
        x11vnc \
        novnc \
        websockify \
        fonts-dejavu-core \
        procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/slotting_optimizer/
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# noVNC's web/WebSocket port - this is the only port that needs to be
# reachable from outside the container.
EXPOSE 6080

ENTRYPOINT ["/entrypoint.sh"]
