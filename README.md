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

A interface é **bilíngue** (pt-BR/en, botão PT/EN no header): as strings ficam em
`src/lib/i18n/{pt,en}.js` e são lidas por `t()` — os dois dicionários têm exatamente as
mesmas chaves. O app é uma **SPA client-side**, com uma exceção: as páginas públicas
(`/g/<slug>` e `/explorar`) são **renderizadas no servidor**, porque são elas que o Google
indexa e que o WhatsApp/Discord desdobram (título, `<meta description>` e Open Graph vêm
prontos no HTML). O SSR renderiza sempre em pt-BR — o navegador corrige o idioma na
hidratação — e busca a API pela rede interna (`POKERDEX_API_INTERNAL_URL`, veja abaixo),
já que para o servidor Node `/api` não é same-origin.

## Migrations (Alembic)

O schema vem **só do Alembic** — não existe mais `create_all`. No startup o app roda
`alembic upgrade head` sozinho (`app/db.py::run_migrations`), então subir o servidor já
migra o banco. Três casos são tratados:

| Estado do banco | O que acontece |
| --- | --- |
| vazio (dev novo) | `upgrade head` cria as 7 tabelas |
| já com `alembic_version` | `upgrade head` aplica o que estiver pendente |
| já com as tabelas, sem `alembic_version` (dev/prod antigos) | `stamp` da revisão inicial + `upgrade head` |

A URL do banco vem **sempre** de `POKERDEX_DATABASE_URL` (via `app.config.settings`):
`alembic.ini` não tem `sqlalchemy.url`, quem define é `alembic/env.py`. Assim a CLI e o
startup migram o mesmo arquivo — inclusive em Docker, onde o banco fica em `/data`.

Para mudanças de schema:
```bash
cd backend
# opcional: aponte para outro banco, senão usa o de .env / o default
export POKERDEX_DATABASE_URL=sqlite:///./pokerdex.db

.venv/bin/alembic revision --autogenerate -m "descrição"   # gere a partir dos models
.venv/bin/alembic upgrade head                             # aplique (o startup também faz)
.venv/bin/alembic current                                  # confira a revisão
.venv/bin/alembic downgrade -1                             # volte uma revisão
```

Revise sempre o arquivo gerado em `alembic/versions/` antes de commitar: bancos antigos
carregam tabelas de versões anteriores do modelo (`gamevariant`, `gameformat`, `stake`,
`nighttag`) e um autogenerate rodado contra eles vai propor `drop_table` nelas.
`tests/test_migrations.py` falha se os models e as migrations divergirem.

## Testes (backend)

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest                     # suíte completa
.venv/bin/pytest -m "not timing"     # sem os testes sensíveis a wall-clock
```

Cada execução usa um SQLite temporário (via `POKERDEX_DATABASE_URL`) migrado pelo Alembic,
igual à produção. `tests/test_queries.py` protege contra N+1: o número de queries de um
request não pode crescer com a quantidade de noites/grupos.

## Deploy na VPS (Docker Compose + Cloudflare)

HTTPS é provido pelo **Cloudflare** (proxy laranja, SSL "Flexible"); o origin só fala
HTTP na porta 80. Um **edge proxy** compartilhado (`deploy/edge`) escuta na 80 e roteia
por subdomínio, então várias apps convivem na mesma VPS sem conflito de porta.

```
Cloudflare (HTTPS) → VPS:80 → edge (Caddy http)
    ├── pokerdex.seudominio.com → /api/* → backend:8000 · / → frontend:3000
    └── (outras apps por subdomínio)
```

**Passos** (Docker já instalado, subdomínio `pokerdex.…` proxied no Cloudflare):

```bash
# rede compartilhada do edge (uma vez só)
docker network create web

# app Pokerdex (sem portas/TLS próprios — fica atrás do edge)
git clone https://github.com/viniaraujo68/pokerdex-v3.git
cd pokerdex-v3
docker compose up -d --build

# edge proxy (porta 80, roteia os subdomínios)
cd deploy/edge
cp .env.example .env     # ajuste POKERDEX_DOMAIN / RASTRO_DOMAIN
docker compose up -d
```

No Cloudflare: registro `pokerdex` (A/CNAME) **proxied (laranja)**, SSL/TLS = **Flexible**.

O SQLite vive no volume `pokerdex_data`
(backup = `docker compose cp backend:/data/pokerdex.db ./backup.db`).

### Importar o histórico antigo (opcional)

1. Crie sua conta de dono pela interface (`/register`).
2. Copie os backups e rode o import dentro do container do backend:
   ```bash
   docker compose cp players.json backend:/tmp/players.json
   docker compose cp nights.json  backend:/tmp/nights.json
   docker compose exec backend python scripts/import_legacy.py \
     --players /tmp/players.json --nights /tmp/nights.json \
     --owner SEU_USUARIO --group-name "Sextodex Legacy" --visibility public
   ```
   O script valida os totais contra o backup e aborta se algo não bater.

### Variáveis de ambiente (backend)

| Variável | Padrão | Descrição |
|---|---|---|
| `POKERDEX_DATABASE_URL` | `sqlite:///./pokerdex.db` | Caminho do banco |
| `POKERDEX_COOKIE_SECURE` | `false` | `true` em produção (HTTPS) |
| `POKERDEX_SESSION_TTL_DAYS` | `30` | Validade da sessão |
| `POKERDEX_CORS_ORIGINS` | `http://localhost:5173` | Vazio em prod (same-origin) |

### Variáveis de ambiente (frontend)

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `3000` | Porta do servidor Node (adapter-node) |
| `ORIGIN` | — | URL pública; o adapter-node precisa dela para montar links absolutos |
| `POKERDEX_API_INTERNAL_URL` | `http://backend:8000` (`http://localhost:8000` em dev) | Onde o **SSR** busca a API. No navegador `/api` continua same-origin (edge/Caddy) |
