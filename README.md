# Pokerdex ♠

Registre as noites de poker do seu grupo: crie grupos com participantes, locais e
tags, lance cada noite com buy-in e cash-out, e acompanhe ranking, ROI, recordes e a
evolução do lucro de cada um. Reescrita moderna do [projeto original](https://github.com/viniaraujo68/pokerdex).

**Stack:** FastAPI + SQLite (backend) · SvelteKit (frontend) · Caddy + Docker Compose (deploy).

## Conceitos

- **Grupo** — unidade central. Tem um ou mais **donos** (contas com login).
- **Participantes** — pessoas do grupo (não são usuários/contas), isolados por grupo.
- **Catálogos por grupo** — locais, variantes, formatos, stakes (enums) e tags livres por noite.
- **Noite** — data, local, e por participante um **buy-in** e um **cash-out**; o lucro é
  calculado (`cash_out − buy_in`). Se o pot não fechar, o app **avisa** mas deixa salvar.
- **Acesso** — slug legível (`/g/meu-grupo`) + visibilidade `public`/`private` +
  `share_token` rotacionável para compartilhar grupos privados.
- Dinheiro é sempre **centavos (inteiro)**; estatísticas são derivadas das noites (sem
  agregados denormalizados), então editar/excluir nunca dessincroniza os totais.

## Rodando em desenvolvimento

**Backend** (porta 8000):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (porta 5173, com proxy de `/api` → 8000):
```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173.

## Migrations (Alembic)

Em dev as tabelas são criadas automaticamente no startup. Para mudanças de schema:
```bash
cd backend
alembic revision --autogenerate -m "descrição"
alembic upgrade head
```

## Deploy na VPS (Docker Compose)

1. Aponte seu domínio (A record) para o IP da VPS.
2. Edite o domínio no `Caddyfile`.
3. Suba tudo:
   ```bash
   docker compose up -d --build
   ```

Caddy cuida do HTTPS automaticamente. O SQLite fica no volume `pokerdex_data`
(backup = copiar `/data/pokerdex.db`).

### Variáveis de ambiente (backend)

| Variável | Padrão | Descrição |
|---|---|---|
| `POKERDEX_DATABASE_URL` | `sqlite:///./pokerdex.db` | Caminho do banco |
| `POKERDEX_COOKIE_SECURE` | `false` | `true` em produção (HTTPS) |
| `POKERDEX_SESSION_TTL_DAYS` | `30` | Validade da sessão |
| `POKERDEX_CORS_ORIGINS` | `http://localhost:5173` | Vazio em prod (same-origin) |
