# zaha-01 deployment (Marie + Zaha demos)

Target: **Docker Compose** on zaha-01, public URLs on **www.theworldavatar.io**.

## Isolation (safe with existing Docker stacks)

- Compose **project name**: `mariecp-demo` — only this stack is built/started/restarted
- Publishes **0.0.0.0:3001** (external on host; nginx proxies via `127.0.0.1:3001`)
- No `apt`, no system Python venv/conda, **no nginx reload** in install script
- Never runs `docker compose down` without `-p mariecp-demo`

## Prerequisites

| Item | Path / note |
|------|-------------|
| Caches | `/home/xz378/mini_marie_data/data/mini_marie_cache/{sg_old,chemistry,twa_city}/` |
| Docker | Engine + Compose v2 |
| LLM key | `REMOTE_API_KEY` in `/home/xz378/mariecp/.env` |
| Outbound HTTPS | theworldavatar.io (Zaha mirror on first start) |

## 1. Test locally first

```powershell
.\demos\run_docker_smoke.ps1
```

## 2. Deploy on zaha-01

```bash
ssh xz378@zaha-01
cd ~/mariecp && git pull
bash deploy/zaha-01/install.sh
```

Edit secrets if needed:

```bash
nano ~/mariecp/.env   # REMOTE_API_KEY, FLASK_SECRET_KEY
docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo up -d --build
```

## 3. nginx (www.theworldavatar.io)

Merge `nginx-mariecp-demo.conf` into the site config (upstream `127.0.0.1:3001`).

```bash
curl -s http://127.0.0.1:3001/health
curl -s http://127.0.0.1:3001/health/cache | python3 -m json.tool
```

## 4. Upgrade

```bash
cd ~/mariecp && git pull
docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo up -d --build
```

## 5. Manage

```bash
docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo ps
docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo logs -f mariecp-demo
```

Stop demo only:

```bash
docker compose --env-file .env -f docker/compose.demo.yml -p mariecp-demo down
```
