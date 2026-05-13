# Implementation Plan – Docker + Ansible + GitHub Actions Deployment

## Goal
Deploy the **Analytics Platform** on the existing Timeweb VPS (Ubuntu 24.04, 4 CPU, 8 GB RAM, 80 GB NVMe) using a fully automated CI/CD pipeline:
- **Docker** – isolates the application and its PostgreSQL database.
- **Ansible** – provisions the VPS (installs Docker, copies project files, sets up environment).
- **GitHub Actions** – runs tests, builds the Docker image, pushes it to GHCR and triggers the Ansible playbook.

The solution is **self‑contained** – no manual steps after the first secret/`.env` setup.

---

## Files Added
| File | Path | Purpose |
|------|------|---------|
| `Dockerfile` | `project_root/Dockerfile` | Builds a minimal Python 3.12 image, installs system deps, copies source, installs `requirements.txt`, runs `run_integration.py`. |
| `docker-compose.yml` | `project_root/docker-compose.yml` | Defines two services: `db` (PostgreSQL) and `app` (our code). Uses a `.env` file for configuration. |
| `ansible_deploy.yml` | `project_root/ansible_deploy.yml` | Installs Docker, copies project files, places `.env`, and runs `docker compose up -d`. |
| `.github/workflows/deploy.yml` | `project_root/.github/workflows/deploy.yml` | CI pipeline: test → build Docker → push to GHCR → SSH → run Ansible on VPS. |
| `templates/analytics.service.j2` | `project_root/templates/analytics.service.j2` | Fallback systemd service template (kept for non‑Docker deployments). |
| `.env.template` | `project_root/.env.template` | Example environment file – copy to `.env` on the server and fill in real credentials. |
| `.gitignore` | `project_root/.gitignore` | Prevents committing secrets, virtualenv, build artifacts, etc. |

---

## Deployment Rules (`deployment-rules.md`)
1. **VPS Requirements** – Ubuntu 24.04, Docker >= 24.0, network access to GHCR.
2. **Environment** – On the VPS create `/opt/analytics_platform/.env` based on `.env.template` (POSTGRES, SMTP, PORT, etc.).
3. **One‑time setup** – Add the SSH public key of the CI runner to `~/.ssh/authorized_keys` on the VPS.
4. **Running** – After the first push, GitHub Actions will automatically:
   - Run unit tests (`pytest`).
   - Build the Docker image and push it to `ghcr.io/<owner>/<repo>:latest`.
   - Execute `ansible_deploy.yml` which installs Docker (if missing) and starts the compose stack.
5. **Updates** – Subsequent pushes repeat the process; no manual server interaction required.
6. **Rollback** – Change the image tag in the workflow or run `docker compose down && docker compose pull && docker compose up -d` manually via SSH.

---

## Verification Plan
### Automated
- **GitHub Actions** will fail the workflow if any test fails or if Docker build fails.
- The final step (`docker compose up -d`) returns exit code 0; any error aborts the job.

### Manual (post‑deployment)
1. Open `http://<VPS_IP>:8000` (or the port defined in `.env`). The app should start `run_integration.py` and log to stdout.
2. Run `ssh <user>@<VPS_IP> "docker ps"` – you should see `app` and `db` containers running.
3. Verify DB connectivity: `ssh <user>@<VPS_IP> "docker exec -it analytics_db psql -U analytics -d analytics_db -c \"\dt\""` – tables from the platform should be listed.
4. Check that new markdown notes appear in the Obsidian vault after processing a sample TXT report.

---

## Next Immediate Actions (already performed)
- Created `Dockerfile`, `docker-compose.yml`, `ansible_deploy.yml`, workflow `deploy.yml`, template `analytics.service.j2`, `.gitignore`, and `.env.template`.
- Updated the repository structure accordingly.
- You now need to:
  1. Add GitHub Secrets (`SSH_PRIVATE_KEY`, `VPS_HOST`, `GIT_REPO_URL`).
  2. Copy `.env.template` → `.env` on the VPS and fill real credentials.
  3. Commit & push the changes to `main` (or `master`).

Once these are done, the CI/CD pipeline will automatically provision the VPS and launch the platform.
