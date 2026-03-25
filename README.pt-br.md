# Automação OCI de Start/Stop

[![English](https://img.shields.io/badge/lang-en-red.svg)](README.md)

> Esta é a versão em português da documentação. [Click here for the English version.](README.md)

---

Aplicação full stack para cadastro, acionamento, agendamento e geração de relatórios operacionais e de custo na OCI.

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

### Tela Custo/Compartimento

A tela `Dashboard > Custo/Compartimento`:

- abre no mês atual por padrão
- permite selecionar mês e ano
- consulta o período salvo no cache local
- permite atualizar manualmente o período a partir da OCI
- exibe o total mensal e os totais por compartimento
- oferece exportação CSV do período selecionado

## Configuração

Variáveis de ambiente relevantes:

- `DATABASE_URL`
- `REPORTS_DATABASE_URL`
- `OCI_CLI_PATH`
- `OCI_CLI_PROFILE`
- `OCI_CONFIG_DIR`
- `REPORTS_OCI_TENANT_ID`
- `SUPPRESS_OCI_LABEL_WARNING`
- `API_BASE_URL`
- `REPORTS_API_BASE_URL`

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
