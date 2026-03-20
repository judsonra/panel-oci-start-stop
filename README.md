# OCI Start/Stop Automation

Aplicacao full stack para cadastro, acionamento e agendamento de instancias OCI.

## Stack

- Frontend Angular + PrimeNG em layout administrativo inspirado no Sakai
- Backend FastAPI + Uvicorn
- PostgreSQL
- Alembic para versionamento estrutural
- OCI CLI executado localmente pelo backend

## Subida local

1. Ajuste as variaveis em `.env.example` ou exporte overrides no shell.
2. Garanta que `~/.oci` do host esteja configurado.
   O backend usa o `oci-cli` instalado na imagem Docker e espera que o diretorio montado contenha pelo menos:
   - `~/.oci/config`
   - chaves/arquivos referenciados no profile configurado
3. Suba os containers:

```bash
docker compose up --build
```

Se o frontend falhar no build com erro de dependencia nativa do Rollup, faca uma limpeza local antes de recriar a imagem:

```bash
rm -rf frontend/node_modules
docker compose build frontend --no-cache
docker compose up --build
```

O `docker-compose` usa um volume dedicado para `/workspace/node_modules`, evitando compartilhar dependencias do host com o container.

Depois da migracao para a base Sakai, o container do frontend passou a validar `package.json` e `package-lock.json` na inicializacao. Quando houver mudanca de dependencias, ele executa `npm ci` automaticamente no volume `frontend-node-modules`, evitando erro por volume antigo ou incompleto.

## Backend

- API em `http://localhost:8000`
- Docs OpenAPI em `http://localhost:8000/docs`
- Health detalhado em `http://localhost:8000/api/health`

## OCI CLI no backend

- O `oci-cli` e instalado dentro do container do backend pelo [backend/Dockerfile](/home/infra/Downloads/oci-start-stop/backend/Dockerfile)
- O perfil usado e controlado por `OCI_CLI_PROFILE`
- O executavel pode ser sobrescrito por `OCI_CLI_PATH`
- O arquivo de configuracao e resolvido a partir de `OCI_CONFIG_DIR/config`

Fluxo de execucao:

1. O frontend envia a acao e o `instance_id`
2. A API busca a instancia cadastrada no banco
3. O backend resolve o `ocid`
4. O servico `OCIService` monta o comando permitido do `oci`
5. O comando e executado localmente no container
6. O resultado e persistido em `execution_logs` e devolvido pela API

## Frontend

- UI em `http://localhost:4200`
- Base oficial do cliente em `frontend/`
- Stack: Angular 21 + PrimeNG 21 + layout Sakai NG
- Nesta fase nao ha tela de login; a aplicacao abre direto no shell principal

### Estrutura do frontend

O repositorio mantem apenas um diretorio de frontend: [frontend](/home/infra/Downloads/oci-start-stop/frontend).

O diretorio temporario `sakai-ng-master` foi removido apos a migracao. A referencia futura para evolucoes visuais e componentes deve ser a documentacao oficial do Sakai/PrimeNG, nao uma copia local do template.

Modulos entregues no menu lateral:

- Dashboard
- Instancias
- Agendamentos
- Execucoes

Arquitetura principal:

- `src/app/layout`: shell do Sakai adaptado para o contexto OCI
- `src/app/core`: `ApiService` e contratos de dados
- `src/app/pages/dashboard`: contadores e resumo operacional
- `src/app/pages/instances`: cadastro, listagem e acoes de ligar/desligar
- `src/app/pages/schedules`: cadastro e listagem de agendamentos
- `src/app/pages/executions`: historico de execucoes
- `src/assets/styles.scss`: identidade visual e ajustes do shell/layout
- `public/app-config.js`: configuracao runtime do endpoint da API

### Desenvolvimento do frontend

```bash
cd frontend
npm install
ng serve
```

Comandos principais:

```bash
cd frontend
ng build
ng test
```

Observacoes:

- o frontend consome os mesmos endpoints do backend em `/api`
- o endpoint real do backend e resolvido em runtime por `API_BASE_URL`, exposto em `public/app-config.js`
- o padrao de testes adotado agora e o nativo do Sakai/Angular com `ng test`
- a integracao com Microsoft Entra ID fica como evolucao futura

## Testes

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
