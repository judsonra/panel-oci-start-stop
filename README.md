# OCI Start/Stop Automation

[![Português](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt-br.md)

> This is the English version of the documentation. [Clique aqui para a versão em Português.](README.pt-br.md)

---

Full-stack application for registering, operating, scheduling, and reporting OCI workloads and costs.

## API Updates

### Backend API (`http://localhost:8000/api`)

- Health:
  - `GET /health`
- Compartments:
  - `GET /compartiments/list`
  - `GET /compartiments/listandupdate`
  - `GET /compartiments/instancesall`
  - `POST /compartiments/instancesall/jobs`
  - `GET /compartiments/instancesall/jobs/{job_id}`
  - `GET /compartiments/instances/{instance_ocid}/vnic`
  - `GET /compartiments/vnics/{vnic_id}`
- Groups:
  - `GET /groups`
  - `GET /groups/tree`
  - `GET /groups/{group_id}`
  - `POST /groups`
  - `PUT /groups/{group_id}`
  - `DELETE /groups/{group_id}`
- Instances:
  - `GET /instances`
  - `POST /instances`
  - `GET /instances/import-preview/{instance_ocid}`
  - `POST /instances/import`
  - `PUT /instances/{instance_id}`
  - `DELETE /instances/{instance_id}`
  - `POST /instances/{instance_id}/start`
  - `POST /instances/{instance_id}/stop`
  - `GET /instances/{instance_id}/status`
- Schedules:
  - `GET /schedules`
  - `POST /schedules`
  - `PUT /schedules/{schedule_id}`
  - `DELETE /schedules/{schedule_id}`
- Executions:
  - `GET /executions`

### Reports API (`http://localhost:8010`)

- Health:
  - `GET /health`
- Cost by compartment:
  - `GET /api/reports/cost-by-compartment?year=YYYY&month=MM`
  - `GET /api/reports/cost-by-compartment.csv?year=YYYY&month=MM`
  - `POST /api/reports/cost-by-compartment/refresh`

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
- Authentication now supports Microsoft Entra ID redirect and an optional hidden local admin login at `/access`

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

Recent frontend improvements:

- Instances:
  - local search on the registered instances table;
  - OCI preview before manual import;
  - edit support in the registration flow;
  - automatic registration progress modal with polling support in the current local codebase.
- Reports:
  - `Cost/Compartment` now uses the `reports` microservice only;
  - month picker input for the reporting period;
  - tabs for monthly totals, daily costs and detailed cost composition;
  - advanced cost composition table with filters and column toggle;
  - richer daily cost composition visualization.

### Cost/Compartment Screen

The `Dashboard > Cost/Compartment` screen:

- opens with the current month by default
- allows selecting month and year
- reads the saved period from the local cache
- allows manually refreshing the selected period from OCI
- shows the monthly total and the compartment totals
- offers CSV export for the selected period

## Environment Variables

The application reads environment variables from `.env` and from `docker-compose.yml`. The table below documents every variable currently used by the containers and runtime frontend configuration.

| Variable | Service(s) | Required | Default | Purpose |
| --- | --- | --- | --- | --- |
| `POSTGRES_DB` | `postgres` | No | `oci_automation` | Creates the initial PostgreSQL database name used by Docker Compose. |
| `POSTGRES_USER` | `postgres` | No | `oci_user` | Creates the PostgreSQL user for the local containerized database. |
| `POSTGRES_PASSWORD` | `postgres` | No | `oci_password` | Sets the PostgreSQL password for the local containerized database. |
| `POSTGRES_PORT` | `postgres` | No | `5432` | Publishes the PostgreSQL container port to the host machine. |
| `DATABASE_URL` | `backend` | Yes | `postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation` | Main SQLAlchemy connection string for the operational backend. |
| `REPORTS_DATABASE_URL` | Compose -> `reports` | Yes | `postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation` | External variable that feeds `DATABASE_URL` inside the `reports` container. |
| `OCI_CLI_PATH` | `backend`, `reports` | No | `oci` | Overrides the OCI CLI executable name or full path used inside the containers. |
| `OCI_CLI_PROFILE` | `backend`, `reports` | No | `DEFAULT` | Selects the OCI CLI profile used for operational commands and report collection. |
| `OCI_CONFIG_DIR` | `backend`, `reports` | Yes | `/home/appuser/.oci` | Directory mounted into the containers that contains `config` and the OCI key material. |
| `REPORTS_OCI_TENANT_ID` | Compose -> `reports` | No | empty | External variable that feeds `OCI_TENANT_ID` inside the `reports` container when tenancy must be forced explicitly. |
| `SUPPRESS_OCI_LABEL_WARNING` | `reports` | No | `true` | Controls whether the reports service suppresses OCI label warnings while normalizing report output. |
| `AUTH_ENABLED` | `backend` | No | `false` | Enables or disables JWT/OIDC authentication enforcement in the operational backend. |
| `OIDC_ISSUER` | `backend` | No | empty | Configures the expected OIDC issuer when authentication is enabled. |
| `OIDC_AUDIENCE` | `backend` | No | empty | Configures the expected token audience when authentication is enabled. |
| `OIDC_JWKS_URL` | `backend` | No | empty | Provides the JWKS endpoint used to validate incoming JWT signatures. |
| `ALLOWED_GROUPS` | `backend` | No | empty | Comma-separated list of identity groups allowed to use the operational backend. |
| `ENTRA_AUTH_ENABLED` | `backend` | No | `false` | Enables Microsoft Entra ID authentication through OpenID Connect/OAuth 2.0 Authorization Code + PKCE. |
| `ENTRA_TENANT_ID` | `backend` | No | empty | Optional Entra tenant identifier for operational configuration and documentation alignment. |
| `ENTRA_CLIENT_ID` | `backend`, `frontend` runtime | No | empty | Public Entra application client ID used during the browser redirect flow. |
| `ENTRA_AUTHORITY` | `backend`, `frontend` runtime | No | empty | Base Entra authority URL used for authorize, token and logout flows. |
| `ENTRA_REDIRECT_URI` | `backend`, `frontend` runtime | No | `http://localhost:4200/auth/callback` | Redirect URI registered in Entra and used by the SPA callback flow. |
| `ENTRA_POST_LOGOUT_REDIRECT_URI` | `backend`, `frontend` runtime | No | `http://localhost:4200/access` | Browser redirect target after a Microsoft logout. |
| `ENTRA_SCOPES` | `backend`, `frontend` runtime | No | `openid profile email` | Space-separated scopes requested during the Entra login flow. |
| `ENTRA_JWKS_URL` | `backend` | No | empty | JWKS endpoint used by the backend to validate Entra ID tokens. |
| `ENTRA_ISSUER` | `backend` | No | empty | Expected issuer claim for validated Entra ID tokens. |
| `ENTRA_AUDIENCE` | `backend` | No | empty | Expected audience claim for validated Entra ID tokens. |
| `LOCAL_ADMIN_ENABLED` | `backend` | No | `false` | Enables the hidden local superadmin login exposed at `/access`. |
| `LOCAL_ADMIN_EMAIL` | `backend` | Yes when `LOCAL_ADMIN_ENABLED=true` | empty | Local superadmin login email. Empty values are rejected when local auth is enabled. |
| `LOCAL_ADMIN_PASSWORD_HASH` | `backend` | Yes when `LOCAL_ADMIN_ENABLED=true` | empty | Bcrypt or Argon2 password hash for the local superadmin login. |
| `LOCAL_AUTH_JWT_SECRET` | `backend` | Yes when any app token is issued | empty | Secret used by the backend to sign local application JWTs. |
| `LOCAL_AUTH_JWT_EXPIRES_MINUTES` | `backend` | No | `480` | Lifetime of locally issued application JWTs in minutes. |
| `APP_TIMEZONE` | `backend` | No | `UTC` | Defines the application timezone used by scheduling and time-based backend behavior. |
| `SCHEDULER_POLL_SECONDS` | `backend` | No | `30` | Controls how often the schedule runner checks for due jobs. |
| `SCHEDULER_ENABLED` | `backend` | No | `true` | Enables or disables the backend scheduler loop at startup. |
| `SCHEDULE_GROUP_MAX_CONCURRENCY` | `backend` | No | `3` | Limits how many instance actions from the same scheduled group can run in parallel during scheduler execution. |
| `CORS_ORIGINS` | `backend`, `reports` | No | `http://localhost:4200,http://127.0.0.1:4200` | Comma-separated list of allowed browser origins for both APIs. |
| `DESKMANAGER_AUTH_URL` | `backend` | Yes | `https://api.desk.ms/Login/autenticar` | URL used to authenticate against DeskManager before ticket creation. |
| `DESKMANAGER_TICKETS_URL` | `backend` | Yes | `https://api.desk.ms/Chamados` | URL of the DeskManager ticket creation endpoint. |
| `DESKMANAGER_APPROVER_TOKEN` | `backend` | Yes | empty | Token sent in the DeskManager authentication header. |
| `DESKMANAGER_PUBLIC_KEY` | `backend` | Yes | empty | Operator public key used to obtain a DeskManager access token. |
| `DESKMANAGER_SOLICITACAO_ID` | `backend` | Yes | `000004` | Value sent as `Solicitacao` when opening tickets. |
| `DESKMANAGER_IMPACTO_ID` | `backend` | Yes | `000002` | Value sent as `Impacto` when opening tickets. |
| `DESKMANAGER_URGENCIA_ID` | `backend` | Yes | `000002` | Value sent as `Urgencia` when opening tickets. |
| `DESKMANAGER_CATEGORIA_ID` | `backend` | Yes | `47859` | Value sent as `Categoria` when opening tickets. |
| `DESKMANAGER_CATEGORIA_TIPO_ID` | `backend` | Yes | `47859` | Value sent as `CategoriaTipo` when opening tickets. |
| `DESKMANAGER_GRUPO_ID` | `backend` | Yes | `000019` | Value sent as `Grupo` when opening tickets. |
| `API_BASE_URL` | `frontend` | No | `http://localhost:8000/api` | Runtime frontend endpoint for the operational backend; injected into `public/app-config.js`. |
| `REPORTS_API_BASE_URL` | `frontend` | No | `http://localhost:8010/api` | Runtime frontend endpoint for the `reports` microservice; injected into `public/app-config.js`. |

Important mappings:

- `REPORTS_DATABASE_URL` is a Compose-level variable that becomes `DATABASE_URL` inside the `reports` container.
- `REPORTS_OCI_TENANT_ID` is a Compose-level variable that becomes `OCI_TENANT_ID` inside the `reports` container.
- `API_BASE_URL`, `REPORTS_API_BASE_URL`, `ENTRA_AUTH_ENABLED`, `LOCAL_ADMIN_ENABLED`, `ENTRA_AUTHORITY`, `ENTRA_CLIENT_ID`, `ENTRA_REDIRECT_URI`, `ENTRA_POST_LOGOUT_REDIRECT_URI`, and `ENTRA_SCOPES` are written at container startup into `frontend/public/app-config.js`.

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
