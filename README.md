# OCI Start/Stop Automation

[![Português](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt-br.md)

> This is the English version of the documentation. [Clique aqui para a versão em Português.](README.pt-br.md)

---

Full-stack application for registering, operating, scheduling, and reporting OCI workloads and costs.

## Stack

- Angular + PrimeNG frontend in an administrative layout inspired by Sakai
- FastAPI + Uvicorn operational backend
- FastAPI + Uvicorn `reports` microservice for cost reporting
- PostgreSQL
- Alembic for structural versioning
- OCI CLI executed locally by the backend and by the `reports` service

## Local Startup

1. Adjust the variables in `.env.example` or export overrides in your shell.
2. Make sure the OCI directory mounted by Docker is configured.
   The backend and `reports` service use the `oci-cli` installed in their Docker images and expect the mounted directory to contain at least:
   - `./oci/config`
   - keys/files referenced by the configured profile
3. Start the containers:

```bash
docker compose up --build
```

This now starts:

- `postgres`
- `backend`
- `reports`
- `frontend`

If the frontend fails during build with a native Rollup dependency error, clean the local environment before rebuilding the image:

```bash
rm -rf frontend/node_modules
docker compose build frontend --no-cache
docker compose up --build
```

The `docker-compose` setup uses a dedicated volume for `/workspace/node_modules`, preventing host dependencies from being shared with the container.

After the migration to the Sakai-based frontend, the frontend container validates `package.json` and `package-lock.json` on startup. When dependencies change, it runs `npm ci` automatically inside the `frontend-node-modules` volume, avoiding failures caused by stale or incomplete volumes.

## Backend

- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Detailed health endpoint: `http://localhost:8000/api/health`

## Reports Service

- Service URL: `http://localhost:8010`
- Healthcheck: `http://localhost:8010/health`

Main endpoints:

- `GET /api/reports/cost-by-compartment?year=YYYY&month=MM`
- `GET /api/reports/cost-by-compartment.csv?year=YYYY&month=MM`
- `POST /api/reports/cost-by-compartment/refresh`

Current reporting flow:

1. The frontend opens `Dashboard > Cost/Compartment`
2. A standard query reads the selected month from the local PostgreSQL cache
3. `refresh` triggers a manual OCI CLI query for the selected period
4. The result is normalized and stored in PostgreSQL
5. Future reads for the same month come from the persisted local cache instead of querying OCI again

The current report already returns:

- monthly total cost
- monthly totals by compartment
- daily series for the selected month
- cost composition details when OCI exposes them

The `reports` service uses the same OCI directory mounted from `./oci`.

## OCI CLI in the Services

- The `oci-cli` is installed inside both the `backend` and `reports` containers
- The active profile is controlled by `OCI_CLI_PROFILE`
- The executable can be overridden by `OCI_CLI_PATH`
- The configuration file is resolved from `OCI_CONFIG_DIR/config`

Operational execution flow:

1. The frontend sends the action and the `instance_id`
2. The API looks up the registered instance in the database
3. The backend resolves the `ocid`
4. The `OCIService` builds the allowed `oci` command
5. The command is executed locally inside the container
6. The result is persisted to `execution_logs` and returned by the API

Reports execution flow:

1. The frontend requests a monthly cost report
2. The `reports` service checks PostgreSQL for the selected month
3. If cached data exists, it is returned immediately
4. If the user explicitly runs `refresh`, the `reports` service queries OCI via CLI
5. The monthly total and compartment breakdown are saved in PostgreSQL for later reuse

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
- Dashboard > Cost/Compartment
- Instances
- Schedules
- Executions

Main architecture:

- `src/app/layout`: Sakai shell adapted to the OCI context
- `src/app/core`: `ApiService` and data contracts
- `src/app/pages/dashboard`: counters and operational overview
- `src/app/pages/reports`: monthly cost reporting by compartment
- `src/app/pages/instances`: registration, listing, and start/stop actions
- `src/app/pages/schedules`: schedule registration and listing
- `src/app/pages/executions`: execution history
- `src/assets/styles.scss`: visual identity and shell/layout adjustments
- `public/app-config.js`: runtime API endpoint configuration

### Cost/Compartment Screen

The `Dashboard > Cost/Compartment` screen:

- opens with the current month by default
- allows selecting month and year
- reads the saved period from the local cache
- allows manually refreshing the selected period from OCI
- shows the monthly total and the compartment totals
- offers CSV export for the selected period

## Configuration

Relevant environment variables:

- `DATABASE_URL`
- `REPORTS_DATABASE_URL`
- `OCI_CLI_PATH`
- `OCI_CLI_PROFILE`
- `OCI_CONFIG_DIR`
- `REPORTS_OCI_TENANT_ID`
- `SUPPRESS_OCI_LABEL_WARNING`
- `API_BASE_URL`
- `REPORTS_API_BASE_URL`

## Frontend Development

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

- the frontend consumes the operational backend under `API_BASE_URL`
- the cost report screen consumes the `reports` service under `REPORTS_API_BASE_URL`
- both runtime endpoints are exposed in `public/app-config.js`
- the test standard follows the native Sakai/Angular approach with `ng test`
- Microsoft Entra ID integration remains a future enhancement

## Tests

Backend:

```bash
cd backend
pytest
```

Reports:

```bash
cd reports
python -m compileall .
```

Frontend:

```bash
cd frontend
ng test --watch=false --browsers=ChromeHeadless
```
