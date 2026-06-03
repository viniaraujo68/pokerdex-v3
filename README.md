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

Pré-requisitos: Docker + Compose na VPS, e um domínio com registro A apontando pro IP.

```bash
# 1. clonar e configurar o domínio
git clone https://github.com/viniaraujo68/pokerdex-v3.git
cd pokerdex-v3
cp .env.example .env
# edite .env e coloque DOMAIN=pokerdex.seudominio.com

# 2. subir tudo (Caddy emite o HTTPS sozinho)
docker compose up -d --build
```

Pronto — o app fica em `https://pokerdex.seudominio.com`. O SQLite vive no volume
`pokerdex_data` (backup = `docker compose cp backend:/data/pokerdex.db ./backup.db`).

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
