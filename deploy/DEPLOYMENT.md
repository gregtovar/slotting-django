# Deploying Slotting Optimizer for Remote Access

This packages the existing Tkinter app, completely unchanged, into a
Docker container with a virtual screen + browser-based VNC (noVNC), so
up to two people can each open their own independent session in a
normal browser tab - nothing to install on their end.

I tested this exact stack (Xvfb + the real app + x11vnc + websockify/
noVNC) end-to-end before writing this guide, so the steps below are
verified to work, not just theoretical.

## 1. Get a small server

You don't need much - this app is lightweight (it's pure-Python, CSV-
backed) and a virtual desktop session is cheap to run. A **1 vCPU / 2 GB
RAM** box is comfortably enough for two occasional sessions.

Recommended, in order of how little setup they require:

| Provider | Plan | Approx. cost | Why |
|---|---|---|---|
| **DigitalOcean** | Basic Droplet, 2 GB RAM | ~$12/mo | Easiest UI for beginners; has a "Docker on Ubuntu" one-click image so Docker is pre-installed |
| **Hetzner Cloud** | CX22 | ~\u20ac4-5/mo | Cheapest of the three for the same specs; EU-based |
| **AWS Lightsail** | 2 GB plan | ~$12/mo | Good if you're already in the AWS ecosystem |

Pick the Ubuntu 24.04 image. If your provider offers a "Docker"
marketplace/one-click image, use that - it saves the Docker install
step below.

## 2. Install Docker (skip if you used a Docker marketplace image)

SSH into the server, then:

```bash
curl -fsSL https://get.docker.com | sh
```

Verify: `docker --version` and `docker compose version` should both print something.

## 3. Copy the project to the server

From your own computer (where you unzipped `SlottingOptimizer.zip`):

```bash
scp -r SlottingOptimizer your_user@your_server_ip:~/SlottingOptimizer
```

(Or `git push` / `rsync` - whatever you're comfortable with. The
`deploy/` folder needs to sit next to the `slotting_optimizer/` folder,
which it already does in the zip.)

## 4. Set real passwords

On the server, inside `~/SlottingOptimizer/deploy/`:

```bash
cp .env.example .env
nano .env   # set SESSION_A_PASSWORD and SESSION_B_PASSWORD to real, different passwords
```

## 5. Build and start both sessions

```bash
cd ~/SlottingOptimizer/deploy
docker compose up -d --build
```

First build takes a couple of minutes (downloading the base image and
packages). Subsequent restarts are instant.

Check both came up clean:

```bash
docker compose ps
docker compose logs -f
```

You should see each container print `[entrypoint] Starting noVNC/websockify on port 6080...` with no errors above it.

## 6. Open the firewall

Only the two noVNC ports need to be reachable:

```bash
sudo ufw allow 6901/tcp
sudo ufw allow 6902/tcp
sudo ufw allow OpenSSH
sudo ufw enable
```

If your cloud provider has its own firewall/security-group UI (DigitalOcean, AWS, etc.), open the same two ports there too.

## 7. Share access

- Person A: `http://<server-ip>:6901/vnc.html` - password = `SESSION_A_PASSWORD`
- Person B: `http://<server-ip>:6902/vnc.html` - password = `SESSION_B_PASSWORD`

That's it - each gets the full app, full-screen, in their browser, completely independent of the other's clicks.

## Stopping / restarting

```bash
docker compose down       # stop both sessions
docker compose up -d      # start them again
docker compose restart session-a   # just bounce one session (e.g. if someone leaves the app in a weird state)
```

## Optional: real HTTPS + a second login

The setup above is fine for "share a link with two people I trust, on
a port not advertised anywhere." `http://` + a VNC password is **not**
encrypted in transit, though - acceptable risk for casual internal use,
not for anything sensitive over an untrusted network.

If you have a domain name and want it done properly: install
[Caddy](https://caddyserver.com/), point a DNS A record at your server
for each session's subdomain, generate password hashes with
`caddy hash-password`, fill them into `deploy/Caddyfile`, then run
Caddy in front of the two noVNC ports. Caddy handles free, automatic
HTTPS (Let's Encrypt) with no extra config. At that point you can
close ports 6901/6902 to the outside world entirely (only let Caddy on
80/443 through the firewall) and point people at
`https://slotting-a.yourdomain.com` instead.

I can walk through this in detail if/when you have a domain to use.

## Known limitation: concurrent saves

Both sessions read/write the same `data/*.csv` files. The app already
saves atomically (so a save can never corrupt the file), but if both
people edit and save a record in the same few seconds, the second save
wins - there's no merge or locking. For two people using this
occasionally, that's a low-probability, low-stakes situation. Worth
revisiting if usage grows.
