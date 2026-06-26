# zaha-01 deployment (Marie + Zaha demos)

Target: **Flask/gunicorn on zaha-01:8080**, public URLs on **www.theworldavatar.io**.

## Docker / existing stacks

This deployment is **isolated**:

- Gunicorn binds **127.0.0.1:8080** only (loopback, not public).
- Only the **`mariecp-demo`** systemd unit is added/restarted — no `docker` commands.
- **nginx** is not modified or reloaded by `install.sh`; merge the snippet manually after review.

If port 8080 is already taken (e.g. by a container), pick another port:

```bash
MARIECP_PORT=8081 INSTALL_SYSTEMD=1 bash deploy/zaha-01/install.sh
```

Update the nginx `upstream mariecp_demo` to match.

## Prerequisites

| Item | Path / note |
|------|-------------|
| Caches | `/home/xz378/mini_marie_data/data/mini_marie_cache/{sg_old,chemistry,twa_city}/` |
| LLM key | `REMOTE_API_KEY` in `/home/xz378/mariecp/.env` (not committed) |
| Python | 3.11+ |
| Outbound HTTPS | theworldavatar.io (mirror), OpenRouter/OpenAI (KGQA) |

## 1. Upload caches (from dev machine)

```bash
# Git Bash / WSL on Windows
export MARIEP_REMOTE=xz378@zaha-01
bash deploy/zaha-01/upload_caches.sh
# or city only: bash deploy/zaha-01/upload_caches.sh city
```

## 2. Install app (on zaha-01)

Debian/Ubuntu needs the venv OS package once (does not touch Docker):

```bash
sudo apt install -y python3.10-venv python3-pip
```

```bash
ssh xz378@zaha-01
git clone https://github.com/TheWorldAvatar/MarieCP.git ~/mariecp   # first time only
cd ~/mariecp
git pull
rm -rf .venv   # if a previous venv create failed halfway
bash deploy/zaha-01/install.sh
```

Edit secrets:

```bash
nano ~/mariecp/.env   # REMOTE_API_KEY, FLASK_SECRET_KEY
```

Enable systemd:

```bash
cd ~/mariecp
INSTALL_SYSTEMD=1 bash deploy/zaha-01/install.sh
```

## 3. nginx (www.theworldavatar.io)

Merge `nginx-mariecp-demo.conf` into the site config. Upstream must reach zaha-01:8080 (same host or internal IP).

Reload nginx after test:

```bash
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/health/cache | python3 -m json.tool
```

Public smoke:

- https://www.theworldavatar.io/demos/hub/
- https://www.theworldavatar.io/demos/zaha/
- https://www.theworldavatar.io/demos/marie-classic/

## 4. Upgrade

```bash
cd ~/mariecp && git pull && bash deploy/zaha-01/install.sh
sudo systemctl restart mariecp-demo
```
