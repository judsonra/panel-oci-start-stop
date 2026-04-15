# Proxy Backend Rollout Runbook

## Variáveis obrigatórias
- `PROXY_API_KEY`: chave compartilhada entre Apache e backend.
- `PROXY_ALLOWED_IPS`: IPs permitidos para chamadas do Apache (CSV).
- `PROXY_START_COOLDOWN_SECONDS`: janela anti-tempestade de start (ex.: `60`).

## Rotação de chave
1. Gerar chave nova forte.
2. Atualizar `PROXY_API_KEY` no backend.
3. Atualizar `PROXY_API_KEY` no Apache.
4. Recarregar Apache e backend.
5. Validar chamada `GET /api/proxy/resolve?host=<host>` com header `X-Proxy-Key`.

## Rollout controlado
1. Habilitar `redirect_backend.lua` em um vhost piloto.
2. Monitorar logs do backend para `decision=pass|wait|error|not_found`.
3. Validar que hosts `RUNNING` passam direto e `STOPPED` entram em espera.
4. Expandir para lote de vhosts após estabilidade.

## Rollback
1. Desabilitar o hook `redirect_backend.lua` no vhost.
2. Reativar `redirect.lua` legado.
3. Recarregar Apache.
4. Manter investigação de causa (chave, conectividade, mapeamento de host, OCI).

## Troubleshooting rápido
- `401 Invalid proxy key`: chave divergente entre Apache e backend.
- `403 Proxy origin is not allowed`: IP do Apache fora de `PROXY_ALLOWED_IPS`.
- `decision=not_found`: `app_url` não cadastrado na instância.
- `decision=error`: falha no status/start OCI ou instância desabilitada.

## Backfill de app_url (produção)

Use este fluxo para preencher `app_url` ausente em registros legados:

1. Disparar job:
   - `POST /api/instances/app-url-backfill/jobs`
2. Consultar progresso:
   - `GET /api/instances/app-url-backfill/jobs/{job_id}`
3. Verificar resultado:
   - `updated`: instâncias preenchidas automaticamente
   - `skipped_existing`: já tinham `app_url` definido
   - `unresolved`: não foi possível derivar host pelo nome; exige ajuste manual
   - `failed`: erro pontual de processamento

Reexecução é segura: instâncias já preenchidas ficam em `skipped_existing`.
