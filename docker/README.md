# MarieCP demo Docker stack

Public demo API + static UIs (Marie classic, Zaha, hub) in an **isolated** Compose project.

## Local test

**PowerShell (Windows):**

```powershell
.\demos\run_docker_smoke.ps1
# optional cache path:
.\demos\run_docker_smoke.ps1 -DataDir "D:\mini_marie_data\data"
```

**Git Bash / Linux:**

```bash
MARIECP_DATA=D:/mini_marie_data/data bash docker/run_demo_smoke.sh
```

Then open http://127.0.0.1:8080/demos/hub/

Stop **only this stack** (does not affect other compose projects):

```bash
docker compose -f docker/compose.demo.yml -p mariecp-demo down
```

## Manual compose

```bash
export MARIECP_DATA=/path/to/mini_marie_data/data
export MARIECP_BIND=127.0.0.1:8080
docker compose -f docker/compose.demo.yml -p mariecp-demo up --build -d
curl http://127.0.0.1:8080/health
```

## Production (zaha-01)

```bash
cd ~/mariecp && git pull
bash deploy/zaha-01/install.sh
```

See [../deploy/zaha-01/README.md](../deploy/zaha-01/README.md).

## Design

| Item | Value |
|------|--------|
| Image | `docker/demo/Dockerfile` |
| Compose file | `docker/compose.demo.yml` |
| Project name | `mariecp-demo` (isolated) |
| Cache mount | `MARIECP_DATA` → `/data` in container |
| Published port | `127.0.0.1:8080` (loopback) |
| Config | `configs/demo_docker.env` + `.env` secrets |

Does **not** run `docker compose down` without `-p mariecp-demo`, does not prune, does not restart unrelated containers.
