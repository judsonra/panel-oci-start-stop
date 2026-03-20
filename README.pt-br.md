# Automação OCI de Start/Stop

[![English](https://img.shields.io/badge/lang-en-red.svg)](README.md)

> Esta é a versão em português da documentação. [Click here for the English version.](README.md)

---

Aplicação full stack para cadastro, acionamento e agendamento de instâncias OCI.

## Stack

- Frontend Angular + PrimeNG em layout administrativo inspirado no Sakai
- Backend FastAPI + Uvicorn
- PostgreSQL
- Alembic para versionamento estrutural
- OCI CLI executado localmente pelo backend

## Subida local

1. Ajuste as variáveis em `.env.example` ou exporte overrides no shell.
2. Garanta que `~/.oci` do host esteja configurado.
   O backend usa o `oci-cli` instalado na imagem Docker e espera que o diretório montado contenha pelo menos:
   - `~/.oci/config`
   - chaves/arquivos referenciados no profile configurado
3. Suba os containers:

```bash
docker compose up --build
```

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

## OCI CLI no backend

- O `oci-cli` é instalado dentro do container do backend pelo `backend/Dockerfile`
- O profile usado é controlado por `OCI_CLI_PROFILE`
- O executável pode ser sobrescrito por `OCI_CLI_PATH`
- O arquivo de configuração é resolvido a partir de `OCI_CONFIG_DIR/config`

Fluxo de execução:

1. O frontend envia a ação e o `instance_id`
2. A API busca a instância cadastrada no banco
3. O backend resolve o `ocid`
4. O serviço `OCIService` monta o comando permitido do `oci`
5. O comando é executado localmente no container
6. O resultado é persistido em `execution_logs` e devolvido pela API

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
- Instâncias
- Agendamentos
- Execuções

Arquitetura principal:

- `src/app/layout`: shell do Sakai adaptado para o contexto OCI
- `src/app/core`: `ApiService` e contratos de dados
- `src/app/pages/dashboard`: contadores e resumo operacional
- `src/app/pages/instances`: cadastro, listagem e ações de ligar/desligar
- `src/app/pages/schedules`: cadastro e listagem de agendamentos
- `src/app/pages/executions`: histórico de execuções
- `src/assets/styles.scss`: identidade visual e ajustes do shell/layout
- `public/app-config.js`: configuração runtime do endpoint da API

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

Observações:

- o frontend consome os mesmos endpoints do backend em `/api`
- o endpoint real do backend é resolvido em runtime por `API_BASE_URL`, exposto em `public/app-config.js`
- o padrão de testes adotado agora é o nativo do Sakai/Angular com `ng test`
- a integração com Microsoft Entra ID fica como evolução futura

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
