# MarieCP demo Docker stack

Public demo API + static UIs (Marie classic, Zaha, hub) in an **isolated** Compose project.

**Default publish:** `0.0.0.0:3001` → container `:8080` (external access on host port 3001).

## Local test

**PowerShell (Windows):**

```powershell
.\demos\run_docker_smoke.ps1
.\demos\run_docker_smoke.ps1 -DataDir "D:\mini_marie_data\data"
```

**Git Bash / Linux:**

```bash
MARIECP_DATA=D:/mini_marie_data/data bash docker/run_demo_smoke.sh
```

Then open http://127.0.0.1:3001/demos/hub/

Stop **only this stack**:

```bash
docker compose -f docker/compose.demo.yml -p mariecp-demo down
```

## Manual compose

```bash
export MARIECP_DATA=/path/to/mini_marie_data/data
export MARIECP_PORT=3001
export MARIECP_PUBLISH_HOST=0.0.0.0
docker compose -f docker/compose.demo.yml -p mariecp-demo up --build -d
curl http://127.0.0.1:3001/health
```

Loopback-only (no external bind):

```bash
MARIECP_PUBLISH_HOST=127.0.0.1 MARIECP_PORT=8080 docker compose -f docker/compose.demo.yml -p mariecp-demo up -d
```

## Production (zaha-01)

```bash
cd ~/mariecp && git pull
bash deploy/zaha-01/install.sh
```

nginx upstream: `127.0.0.1:3001` (see `deploy/zaha-01/nginx-mariecp-demo.conf`).

## Design

| Item | Value |
|------|--------|
| Image | `docker/demo/Dockerfile` |
| Compose file | `docker/compose.demo.yml` |
| Project name | `mariecp-demo` (isolated) |
| Cache mount | `MARIECP_DATA` → `/data` in container |
| Host port | `MARIECP_PORT` (default **3001**) |
| Bind address | `MARIECP_PUBLISH_HOST` (default **0.0.0.0**) |
| Config | `configs/demo_docker.env` + `.env` secrets |

Does **not** run `docker compose down` without `-p mariecp-demo`, does not prune, does not restart unrelated containers.
