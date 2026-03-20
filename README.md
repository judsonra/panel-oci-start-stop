# OCI Start/Stop Automation

[![Português](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt-br.md)

> This is the English version of the documentation. [Clique aqui para a versão em Português.](README.pt-br.md)

---

Full-stack application for registering, operating, and scheduling OCI instances.

## Stack

- Angular + PrimeNG frontend in an administrative layout inspired by Sakai
- FastAPI + Uvicorn backend
- PostgreSQL
- Alembic for structural versioning
- OCI CLI executed locally by the backend

## Local Startup

1. Adjust the variables in `.env.example` or export overrides in your shell.
2. Make sure the host `~/.oci` directory is configured.
   The backend uses the `oci-cli` installed in the Docker image and expects the mounted directory to contain at least:
   - `~/.oci/config`
   - keys/files referenced by the configured profile
3. Start the containers:

```bash
docker compose up --build
```

If the frontend fails during build with a native Rollup dependency error, clean the local environment before rebuilding the image:

```bash
rm -rf frontend/node_modules
docker compose build frontend --no-cache
docker compose up --build
```

The `docker-compose` setup uses a dedicated volume for `/workspace/node_modules`, preventing host dependencies from being shared with the container.

After the migration to the Sakai-based frontend, the frontend container now validates `package.json` and `package-lock.json` on startup. When dependencies change, it runs `npm ci` automatically inside the `frontend-node-modules` volume, avoiding failures caused by stale or incomplete volumes.

## Backend

- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Detailed health endpoint: `http://localhost:8000/api/health`

## OCI CLI in the Backend

- The `oci-cli` is installed inside the backend container by `backend/Dockerfile`
- The active profile is controlled by `OCI_CLI_PROFILE`
- The executable can be overridden by `OCI_CLI_PATH`
- The configuration file is resolved from `OCI_CONFIG_DIR/config`

Execution flow:

1. The frontend sends the action and the `instance_id`
2. The API looks up the registered instance in the database
3. The backend resolves the `ocid`
4. The `OCIService` builds the allowed `oci` command
5. The command is executed locally inside the container
6. The result is persisted to `execution_logs` and returned by the API

## Frontend

- UI: `http://localhost:4200`
- Official client base: `frontend/`
- Stack: Angular 21 + PrimeNG 21 + Sakai NG layout
- At this stage there is no login screen; the application opens directly in the main shell

### Frontend Structure

The repository keeps only one frontend directory: `frontend/`.

The temporary `sakai-ng-master` directory was removed after the migration. Future reference for visual evolution and components should come from the official Sakai/PrimeNG documentation, not from a local copy of the template.

Delivered modules in the sidebar menu:

- Dashboard
- Instances
- Schedules
- Executions

Main architecture:

- `src/app/layout`: Sakai shell adapted to the OCI context
- `src/app/core`: `ApiService` and data contracts
- `src/app/pages/dashboard`: counters and operational overview
- `src/app/pages/instances`: registration, listing, and start/stop actions
- `src/app/pages/schedules`: schedule registration and listing
- `src/app/pages/executions`: execution history
- `src/assets/styles.scss`: visual identity and shell/layout adjustments
- `public/app-config.js`: runtime API endpoint configuration

### Frontend Development

```bash
cd frontend
npm install
ng serve
```

Main commands:

```bash
cd frontend
ng build
ng test
```

Notes:

- the frontend consumes the same backend endpoints under `/api`
- the real backend endpoint is resolved at runtime through `API_BASE_URL`, exposed in `public/app-config.js`
- the test standard now follows the native Sakai/Angular approach with `ng test`
- Microsoft Entra ID integration remains a future enhancement

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
ng test --watch=false --browsers=ChromeHeadless
```
