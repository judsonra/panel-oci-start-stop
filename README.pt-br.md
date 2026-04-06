# Automação OCI de Start/Stop

[![English](https://img.shields.io/badge/lang-en-red.svg)](README.md)

> Esta é a versão em português da documentação. [Click here for the English version.](README.md)

---

Aplicação full stack para cadastro, acionamento, agendamento e geração de relatórios operacionais e de custo na OCI.

## Mudanças recentes (últimos 7 dias)

Janela de cobertura: 31 de março de 2026 a 5 de abril de 2026.

- Compartimentos e sincronização com OCI:
  - listagem de compartimentos e sincronização via `listandupdate` foram adicionadas ao backend operacional e expostas no menu lateral.
- Registro automático de instâncias:
  - o fluxo de importação em lote de todos os compartimentos ativos foi introduzido;
  - o código local atual já inclui um fluxo assíncrono com job + polling para `Registro Automático`, com detalhes de progresso na UI.
- Melhorias na tela de instâncias:
  - busca local por nome, OCID e IPs;
  - preview OCI antes de salvar;
  - edição de instâncias na tela de cadastro;
  - enriquecimento de VNIC e IPs durante a importação via OCI.
- Agendamentos:
  - suporte a agendamento de execução única foi adicionado na tela de agendamentos.
- Grupos:
  - CRUD de grupos, árvore de grupos e relacionamento entre instâncias e grupos foram adicionados.
- Relatório Custo/Compartimento:
  - a tela foi redesenhada com seletor de período, abas, tabela avançada de composição, exportação CSV e detalhamento mais rico vindo do microserviço `reports`.

## Atualizações de API

### Backend API (`http://localhost:8000/api`)

- Health:
  - `GET /health`
- Compartimentos:
  - `GET /compartiments/list`
  - `GET /compartiments/listandupdate`
  - `GET /compartiments/instancesall`
  - `POST /compartiments/instancesall/jobs`
  - `GET /compartiments/instancesall/jobs/{job_id}`
  - `GET /compartiments/instances/{instance_ocid}/vnic`
  - `GET /compartiments/vnics/{vnic_id}`
- Grupos:
  - `GET /groups`
  - `GET /groups/tree`
  - `GET /groups/{group_id}`
  - `POST /groups`
  - `PUT /groups/{group_id}`
  - `DELETE /groups/{group_id}`
- Instâncias:
  - `GET /instances`
  - `POST /instances`
  - `GET /instances/import-preview/{instance_ocid}`
  - `POST /instances/import`
  - `PUT /instances/{instance_id}`
  - `DELETE /instances/{instance_id}`
  - `POST /instances/{instance_id}/start`
  - `POST /instances/{instance_id}/stop`
  - `GET /instances/{instance_id}/status`
- Agendamentos:
  - `GET /schedules`
  - `POST /schedules`
  - `PUT /schedules/{schedule_id}`
  - `DELETE /schedules/{schedule_id}`
- Execuções:
  - `GET /executions`

### Reports API (`http://localhost:8010`)

- Health:
  - `GET /health`
- Custo por compartimento:
  - `GET /api/reports/cost-by-compartment?year=YYYY&month=MM`
  - `GET /api/reports/cost-by-compartment.csv?year=YYYY&month=MM`
  - `POST /api/reports/cost-by-compartment/refresh`

## Stack

- Frontend Angular + PrimeNG em layout administrativo inspirado no Sakai
- Backend operacional FastAPI + Uvicorn
- Microserviço `reports` em FastAPI + Uvicorn para relatórios de custo
- PostgreSQL
- Alembic para versionamento estrutural
- OCI CLI executado localmente pelo backend e pelo serviço `reports`

## Subida local

1. Ajuste as variáveis em `.env.example` ou exporte overrides no shell.
2. Garanta que o diretório OCI montado pelo Docker esteja configurado.
   O backend e o serviço `reports` usam o `oci-cli` instalado nas imagens Docker e esperam que o diretório montado contenha pelo menos:
   - `./oci/config`
   - chaves/arquivos referenciados no profile configurado
3. Suba os containers:

```bash
docker compose up --build
```

Isso agora sobe:

- `postgres`
- `backend`
- `reports`
- `frontend`

Se o frontend falhar no build com erro de dependência nativa do Rollup, faça uma limpeza local antes de recriar a imagem:

```bash
rm -rf frontend/node_modules
docker compose build frontend --no-cache
docker compose up --build
```

O `docker-compose` usa um volume dedicado para `/workspace/node_modules`, evitando compartilhar dependências do host com o container.

Depois da migração para a base Sakai, o container do frontend passou a validar `package.json` e `package-lock.json` na inicialização. Quando houver mudança de dependências, ele executa `npm ci` automaticamente no volume `frontend-node-modules`, evitando erro por volume antigo ou incompleto.

## Backend

- API em `http://localhost:8000`
- Docs OpenAPI em `http://localhost:8000/docs`
- Health detalhado em `http://localhost:8000/api/health`

## Serviço Reports

- URL do serviço: `http://localhost:8010`
- Healthcheck: `http://localhost:8010/health`

Principais endpoints:

- `GET /api/reports/cost-by-compartment?year=YYYY&month=MM`
- `GET /api/reports/cost-by-compartment.csv?year=YYYY&month=MM`
- `POST /api/reports/cost-by-compartment/refresh`

Fluxo atual do relatório:

1. O frontend abre `Dashboard > Custo/Compartimento`
2. A consulta padrão lê o mês selecionado no cache local do PostgreSQL
3. O `refresh` dispara uma consulta manual na OCI via CLI para o período selecionado
4. O resultado é normalizado e gravado no PostgreSQL
5. As próximas leituras do mesmo mês passam a usar o cache persistido no banco local, sem consultar a OCI novamente

O relatório atual já entrega:

- custo mensal total
- totais mensais por compartimento
- série diária do mês selecionado
- detalhamento da composição do custo quando a OCI disponibiliza esse nível de detalhe

O serviço `reports` usa o mesmo diretório OCI montado a partir de `./oci`.

## OCI CLI nos serviços

- O `oci-cli` é instalado dentro dos containers `backend` e `reports`
- O profile usado é controlado por `OCI_CLI_PROFILE`
- O executável pode ser sobrescrito por `OCI_CLI_PATH`
- O arquivo de configuração é resolvido a partir de `OCI_CONFIG_DIR/config`

Fluxo operacional:

1. O frontend envia a ação e o `instance_id`
2. A API busca a instância cadastrada no banco
3. O backend resolve o `ocid`
4. O serviço `OCIService` monta o comando permitido do `oci`
5. O comando é executado localmente no container
6. O resultado é persistido em `execution_logs` e devolvido pela API

Fluxo do relatório:

1. O frontend solicita o relatório mensal de custo
2. O serviço `reports` verifica no PostgreSQL se o mês já está salvo
3. Se houver cache, o retorno vem imediatamente do banco local
4. Se o usuário executar `refresh`, o serviço `reports` consulta a OCI via CLI
5. O total mensal e os custos por compartimento são gravados no PostgreSQL para reutilização futura

## Frontend

- UI em `http://localhost:4200`
- Base oficial do cliente em `frontend/`
- Stack: Angular 21 + PrimeNG 21 + layout Sakai NG
- Nesta fase não há tela de login; a aplicação abre direto no shell principal

### Estrutura do frontend

O repositório mantém apenas um diretório de frontend: `frontend/`.

O diretório temporário `sakai-ng-master` foi removido após a migração. A referência futura para evoluções visuais e componentes deve ser a documentação oficial do Sakai/PrimeNG, não uma cópia local do template.

Módulos entregues no menu lateral:

- Dashboard
- Dashboard > Custo/Compartimento
- Instâncias
- Agendamentos
- Execuções

Arquitetura principal:

- `src/app/layout`: shell do Sakai adaptado para o contexto OCI
- `src/app/core`: `ApiService` e contratos de dados
- `src/app/pages/dashboard`: contadores e resumo operacional
- `src/app/pages/reports`: relatório mensal de custo por compartimento
- `src/app/pages/instances`: cadastro, listagem e ações de ligar/desligar
- `src/app/pages/schedules`: cadastro e listagem de agendamentos
- `src/app/pages/executions`: histórico de execuções
- `src/assets/styles.scss`: identidade visual e ajustes do shell/layout
- `public/app-config.js`: configuração runtime dos endpoints das APIs

Melhorias recentes do frontend:

- Instâncias:
  - busca local na tabela de instâncias cadastradas;
  - preview OCI antes da importação manual;
  - suporte a edição no fluxo de cadastro;
  - modal de progresso do `Registro Automático` com polling no estado atual do código local.
- Relatórios:
  - `Custo/Compartimento` agora usa apenas o microserviço `reports`;
  - seletor de mês para o período do relatório;
  - abas para totais mensais, custos diários e composição detalhada;
  - tabela avançada de composição com filtros e seleção de colunas;
  - visualização mais rica da composição diária de custo.

### Tela Custo/Compartimento

A tela `Dashboard > Custo/Compartimento`:

- abre no mês atual por padrão
- permite selecionar mês e ano
- consulta o período salvo no cache local
- permite atualizar manualmente o período a partir da OCI
- exibe o total mensal e os totais por compartimento
- oferece exportação CSV do período selecionado

## Variáveis de ambiente

A aplicação lê variáveis de ambiente a partir de `.env` e de `docker-compose.yml`. A tabela abaixo documenta todas as variáveis usadas atualmente pelos containers e pela configuração runtime do frontend.

| Variável | Serviço(s) | Obrigatória | Padrão | Utilidade |
| --- | --- | --- | --- | --- |
| `POSTGRES_DB` | `postgres` | Não | `oci_automation` | Define o nome inicial do banco PostgreSQL criado pelo Docker Compose. |
| `POSTGRES_USER` | `postgres` | Não | `oci_user` | Define o usuário PostgreSQL do ambiente local em container. |
| `POSTGRES_PASSWORD` | `postgres` | Não | `oci_password` | Define a senha PostgreSQL do ambiente local em container. |
| `POSTGRES_PORT` | `postgres` | Não | `5432` | Publica a porta do container PostgreSQL para a máquina host. |
| `DATABASE_URL` | `backend` | Sim | `postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation` | String principal de conexão SQLAlchemy do backend operacional. |
| `REPORTS_DATABASE_URL` | Compose -> `reports` | Sim | `postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation` | Variável externa que alimenta `DATABASE_URL` dentro do container `reports`. |
| `OCI_CLI_PATH` | `backend`, `reports` | Não | `oci` | Sobrescreve o nome ou caminho completo do executável OCI CLI usado nos containers. |
| `OCI_CLI_PROFILE` | `backend`, `reports` | Não | `DEFAULT` | Seleciona o profile OCI CLI usado nas operações e na coleta de relatórios. |
| `OCI_CONFIG_DIR` | `backend`, `reports` | Sim | `/home/appuser/.oci` | Diretório montado nos containers que contém o `config` e os arquivos de chave da OCI. |
| `REPORTS_OCI_TENANT_ID` | Compose -> `reports` | Não | vazio | Variável externa que alimenta `OCI_TENANT_ID` no container `reports` quando a tenancy precisa ser forçada explicitamente. |
| `SUPPRESS_OCI_LABEL_WARNING` | `reports` | Não | `true` | Controla se o serviço `reports` deve suprimir avisos de label da OCI durante a normalização do relatório. |
| `AUTH_ENABLED` | `backend` | Não | `false` | Habilita ou desabilita a validação de autenticação JWT/OIDC no backend operacional. |
| `OIDC_ISSUER` | `backend` | Não | vazio | Configura o emissor OIDC esperado quando a autenticação está habilitada. |
| `OIDC_AUDIENCE` | `backend` | Não | vazio | Configura a audience esperada do token quando a autenticação está habilitada. |
| `OIDC_JWKS_URL` | `backend` | Não | vazio | Informa a URL JWKS usada para validar a assinatura dos JWTs recebidos. |
| `ALLOWED_GROUPS` | `backend` | Não | vazio | Lista separada por vírgulas com os grupos de identidade autorizados a usar o backend operacional. |
| `APP_TIMEZONE` | `backend` | Não | `UTC` | Define o timezone da aplicação para comportamento de agendamento e regras temporais do backend. |
| `SCHEDULER_POLL_SECONDS` | `backend` | Não | `30` | Controla o intervalo de verificação do scheduler para encontrar execuções pendentes. |
| `SCHEDULER_ENABLED` | `backend` | Não | `true` | Habilita ou desabilita o loop do scheduler na inicialização do backend. |
| `SCHEDULE_GROUP_MAX_CONCURRENCY` | `backend` | Não | `3` | Limita quantas ações de instâncias do mesmo grupo agendado podem ser executadas em paralelo durante a execução do scheduler. |
| `CORS_ORIGINS` | `backend`, `reports` | Não | `http://localhost:4200,http://127.0.0.1:4200` | Lista separada por vírgulas com as origens permitidas para chamadas de navegador às APIs. |
| `DESKMANAGER_AUTH_URL` | `backend` | Sim | `https://api.desk.ms/Login/autenticar` | URL usada para autenticar no DeskManager antes de abrir chamados. |
| `DESKMANAGER_TICKETS_URL` | `backend` | Sim | `https://api.desk.ms/Chamados` | URL do endpoint de criação de chamados do DeskManager. |
| `DESKMANAGER_APPROVER_TOKEN` | `backend` | Sim | vazio | Token usado no header de autenticação do DeskManager. |
| `DESKMANAGER_PUBLIC_KEY` | `backend` | Sim | vazio | Chave pública do operador usada para obter o access token no DeskManager. |
| `DESKMANAGER_SOLICITACAO_ID` | `backend` | Sim | `000004` | Valor enviado no campo `Solicitacao` ao abrir chamados. |
| `DESKMANAGER_IMPACTO_ID` | `backend` | Sim | `000002` | Valor enviado no campo `Impacto` ao abrir chamados. |
| `DESKMANAGER_URGENCIA_ID` | `backend` | Sim | `000002` | Valor enviado no campo `Urgencia` ao abrir chamados. |
| `DESKMANAGER_CATEGORIA_ID` | `backend` | Sim | `47859` | Valor enviado no campo `Categoria` ao abrir chamados. |
| `DESKMANAGER_CATEGORIA_TIPO_ID` | `backend` | Sim | `47859` | Valor enviado no campo `CategoriaTipo` ao abrir chamados. |
| `DESKMANAGER_GRUPO_ID` | `backend` | Sim | `000019` | Valor enviado no campo `Grupo` ao abrir chamados. |
| `API_BASE_URL` | `frontend` | Não | `http://localhost:8000/api` | Endpoint runtime do frontend para o backend operacional; injetado em `public/app-config.js`. |
| `REPORTS_API_BASE_URL` | `frontend` | Não | `http://localhost:8010/api` | Endpoint runtime do frontend para o microserviço `reports`; injetado em `public/app-config.js`. |

Mapeamentos importantes:

- `REPORTS_DATABASE_URL` é uma variável no Compose que se torna `DATABASE_URL` dentro do container `reports`.
- `REPORTS_OCI_TENANT_ID` é uma variável no Compose que se torna `OCI_TENANT_ID` dentro do `reports`.
- `API_BASE_URL` e `REPORTS_API_BASE_URL` são gravadas em runtime no `frontend/public/app-config.js` e depois consumidas pelo `ApiService` no navegador.

## Desenvolvimento do frontend

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

Observações:

- o frontend consome o backend operacional por `API_BASE_URL`
- a tela de custo consome o serviço `reports` por `REPORTS_API_BASE_URL`
- ambos os endpoints são expostos em runtime por `public/app-config.js`
- o padrão de testes adotado é o nativo do Sakai/Angular com `ng test`
- a integração com Microsoft Entra ID fica como evolução futura

## Testes

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
