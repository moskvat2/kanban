# Sistema Kanban

Sistema de quadro kanban com **React + Vite + TypeScript** (frontend), **Python FastAPI** (backend) e **MySQL**, tudo orquestrado com **Docker Compose**.

---

## Índice

- [Stack](#stack)
- [Funcionalidades](#funcionalidades)
- [Como rodar](#como-rodar)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Estrutura do projeto](#estrutura-do-projeto)
- [API](#api)
- [Lógica de andamento do projeto](#lógica-de-andamento-do-projeto)
- [Detalhes por camada](#detalhes-por-camada)
- [Docker](#docker)

---

## Stack

| Camada    | Tecnologia |
|-----------|------------|
| Frontend  | React 18, TypeScript, Vite, react-router-dom, @hello-pangea/dnd (drag & drop), Axios |
| Backend   | FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT (autenticação JWT), bcrypt |
| Banco     | MySQL 8.4 |
| Servidor  | Uvicorn (com reload) |
| Infra     | Docker Compose |

---

## Funcionalidades

- **Autenticação JWT** — registro, login e consulta do usuário autenticado (senhas com hash bcrypt).
- **CRUD completo** de quadros, colunas e cartões.
- **Drag & drop** — arrastar cartões entre colunas e reordenar colunas, com atualização otimista (UI reage antes da API, com rollback via recarga em caso de erro).
- **Autorização por proprietário** — cada usuário só acessa e cadastra dados em seus próprios quadros (404/403 nos recursos de terceiros).
- **Andamento do projeto** — cada quadro exibe na tela inicial uma barra de progresso calculada com base nos cartões concluídos (ver [lógica](#lógica-de-andamento-do-projeto)).
- **Barra superior (Topbar)** — logotipo, menu de navegação, título da página e menu do usuário ativo (avatar com iniciais, nome, e-mail e logout).

---

## Como rodar

Pré-requisitos: Docker e Docker Compose instalados.

### Modo desenvolvimento (padrão)

```bash
cp .env.example .env   # ajuste as credenciais se desejar
docker compose up -d --build
```

Características do modo dev: servidores com recarga automática, código montado por volume e portas expostas para depuração.

### Modo produção (seguro)

```bash
cp .env.prod.example .env.prod   # TROQUE todos os segredos antes de prosseguir
docker compose -f docker-compose.prod.yml up -d --build
```

Características do modo produção:

- **Banco e backend sem portas expostas** (comunicam-se apenas na rede interna do Docker).
- **Frontend estático servido pelo nginx** — conteiner nginx compila o `dist` com headers de segurança (CSP, `nosniff`, `X-Frame-Options`, etc.) e faz proxy de `/api` para o backend.
- **Backend com usuário não-root** e uvicorn multi-worker.
- Imagens imutáveis (sem volume de código).

> **Importante:** em produção, gere chaves fortes e nunca use os valores de exemplo. Gere a chave JWT com `openssl rand -hex 32`.

Acessos:

| Aplicação            | URL                     |
|----------------------|-------------------------|
| Frontend (dev)       | http://localhost:5173   |
| Frontend (produção)  | http://localhost        |
| Swagger UI (Backend) | http://localhost:8000/docs |
| Health check         | http://localhost:8000/api/health |

Para derrubar e remover os dados:

```bash
docker compose down -v                     # dev
docker compose -f docker-compose.prod.yml down -v   # produção
```

---

## Variáveis de ambiente

Arquivo `.env` (referência em `.env.example`):

| Variável                    | Descrição                                | Default        |
|-----------------------------|------------------------------------------|----------------|
| `MYSQL_DATABASE`            | Nome do banco MySQL                      | `kanban`       |
| `MYSQL_USER`                | Usuário do banco                         | `kanban`       |
| `MYSQL_PASSWORD`            | Senha do usuário do banco                | `kanban_dev_password` |
| `MYSQL_ROOT_PASSWORD`       | Senha do root do MySQL                   | `root_dev_password` |
| `JWT_SECRET_KEY`            | Chave secreta para assinar os tokens JWT | `dev-secret-key-change-me-in-production` |
| `JWT_ALGORITHM`             | Algoritmo de assinatura do JWT           | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token em minutos           | `1440` |
| `CORS_ORIGINS`              | Origens permitidas no CORS (separadas por vírgula) | `http://localhost:5173` |

> **Segurança:** troque `JWT_SECRET_KEY` antes de publicar em produção.

---

## Estrutura do projeto

```
kanban/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # app FastAPI + CORS + registro de rotas
│       ├── core/                  # configuração, segurança e dependências
│       │   ├── config.py          # Settings via pydantic-settings (.env)
│       │   ├── security.py        # hash/verify de senha e criação/decodificação de JWT
│       │   └── security_deps.py   # get_current_user e get_board_for_user
│       ├── db/
│       │   └── database.py        # engine SQLAlchemy, SessionLocal e Base
│       ├── models/                # ORM: User, Board, Column, Card
│       │   └── __init__.py
│       ├── schemas/               # schemas Pydantic (validação de entrada/saída)
│       │   ├── user.py
│       │   └── board.py
│       └── routers/               # endpoints da API
│           ├── auth.py
│           ├── boards.py
│           └── cards.py
└── frontend/
    ├── Dockerfile
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts             # proxy /api -> backend
    └── src/
        ├── main.tsx               # bootstrap React + Router + AuthProvider
        ├── App.tsx                # rotas (login, dashboard e quadro)
        ├── api/
        │   ├── client.ts          # instância Axios + interceptores (token, 401)
        │   └── boards.ts          # authApi, boardsApi, cardsApi
        ├── components/
        │   ├── ErrorBoundary.tsx  # captura erros de renderização
        │   ├── ProtectedRoute.tsx # rota protegida por autenticação
        │   └── Topbar.tsx         # logo, menu de navegação e menu do usuário
        ├── context/
        │   └── AuthContext.tsx    # estado global de autenticação (login/registro/logout)
        ├── pages/
        │   ├── LoginPage.tsx      # login e registro
        │   ├── Dashboard.tsx      # listagem de quadros + barra de progresso
        │   └── BoardPage.tsx      # quadro kanban com drag & drop
        ├── styles/
        │   └── global.css         # CSS global (tema dark, topo, quadro, modal)
        ├── types/
        │   └── index.ts           # tipos TypeScript (User, Board, Card, ...)
        └── utils/
            └── colors.ts          # paleta de acentuação por id
```

---

## API

### Saúde

- `GET /api/health` — status do serviço (`{"status": "ok"}`)

### Autenticação

- `POST /api/auth/register` — criar conta `{name, email, password}` → retorna JWT + usuário
- `POST /api/auth/login` — entrar `{email, password}` → retorna JWT + usuário
- `GET /api/auth/me` — dados do usuário autenticado (Bearer token)

### Quadros (exige `Authorization: Bearer <token>`)

| Método | Rota                            | Descrição |
|--------|---------------------------------|-----------|
| GET    | `/api/boards`                   | Lista os quadros do usuário com resumo de andamento |
| POST   | `/api/boards`                   | Cria um quadro `{title, description?}` |
| GET    | `/api/boards/{id}`              | Detalhe com colunas e cartões |
| PATCH  | `/api/boards/{id}`              | Atualiza `{title?, description?}` |
| DELETE | `/api/boards/{id}`              | Exclui o quadro (e conteúdo em cascata) |
| POST   | `/api/boards/{id}/columns`      | Cria coluna `{title}` |
| PATCH  | `/api/boards/columns/{id}`      | Renomeia coluna `{title}` |
| DELETE | `/api/boards/columns/{id}`      | Exclui coluna e reordena as demais |
| PATCH  | `/api/boards/{id}/columns/reorder` | Reordena colunas (body: lista `{id, position}`) |

### Cartões

| Método | Rota                        | Descrição |
|--------|-----------------------------|-----------|
| POST   | `/api/columns/{id}/cards`   | Cria cartão `{title, description?}` |
| PATCH  | `/api/cards/{id}`           | Atualiza `{title?, description?}` |
| DELETE | `/api/cards/{id}`           | Exclui cartão e reordena a coluna |
| POST   | `/api/cards/{id}/move`      | Move cartão (body: `{column_id, position}`) |

---

## Lógica de andamento do projeto

A tela inicial (`GET /api/boards`) retorna para cada quadro um resumo com:

```json
{
  "progress": 0.25,
  "cards_count": 4,
  "done_cards": 1,
  "columns_count": 3
}
```

O **progresso** é definido como a proporção de cartões **concluídos**, onde concluído = estar na **última coluna** (a coluna com maior posição, normalmente a "Concluído"):

```
progresso = cartões na última coluna / total de cartões
```

Exemplo: 4 cartões, 1 na coluna "Concluído" → `progress = 25%` (os demais somam os 75% restantes).

Tratativas:

- Sem cartões no quadro → `progress = 0` (frontend mostra "Sem cartões ainda").
- Quadro sem colunas → `progress = 0`.
- O resumo também informa `cards_count`, `done_cards` e `columns_count` para exibição de "X de Y concluídos".

---

## Detalhes por camada

### Backend

- **Modelos (`app/models/__init__.py`)**: `User`, `Board`, `Column` e `Card`, com relacionamentos em cascata (`all, delete-orphan`) e ordenação por `position`.
- **Segurança (`core/security*.py`)**: senhas com `bcrypt`; tokens JWT assinados com `JWT_SECRET_KEY`; dependências `get_current_user` e `get_board_for_user` garantem que quem consulta é o dono do recurso.
- **Autorização**: rotas de colunas/cartões checam `column.board.owner_id == user.id`; quadros checam `board.owner_id == user.id`.
- **Ordenação**: colunas e cartões mantêm uma posição inteira e são renumerados ao excluir/mover (funções `_renumber_*`).
- **Tabelas**: criadas automaticamente via `Base.metadata.create_all`.

### Frontend

- **Autenticação (`context/AuthContext.tsx`)**: mantém o usuário logado, restaura a sessão pelo token no `localStorage` e expõe `login`, `register` e `logout`.
- **Cliente HTTP (`api/client.ts`)**: injeta o `Bearer` token em todas as requisições e redireciona para `/login` em resposta de status `401` (exceto nas rotas de autenticação).
- **Drag & drop (`pages/BoardPage.tsx`)**: usa `@hello-pangea/dnd`. A UI é atualizada de forma otimista e sincronizada com a API; em caso de falha o quadro é recarregado.
- **Topbar (`components/Topbar.tsx`)**: logotipo clicável (volta para "Meus quadros"), menu de navegação, título da página, ações customizadas e menu do usuário (avatar com iniciais, nome, e-mail e logout).
- **Progresso (`pages/Dashboard.tsx`)**: cada cartão de quadro exibe barra de progresso, percentual e contagem "X de Y concluídos".
- **Responsividade/scroll**: o canvas do quadro rola horizontalmente; colunas possuem largura fixa de 300px.

### Ajustes importantes de CSS para o drag & drop

Para o drag & drop funcionar corretamente no `@hello-pangea/dnd`, dois detalhes são respeitados no CSS:

- **Animações** com `transform` + `animation-fill-mode: both` nos itens arrastáveis são evitadas (usar apenas `opacity`), pois sobrescrevem o `transform` inline aplicado pela biblioteca ao mover o item.
- **`backdrop-filter`/`filter`/`transform`** não devem estar em ancestrais de itens arrastáveis, pois criam *containing block* e quebram o `position: fixed` usado durante o arrasto (o cartão "pula" para uma posição aleatória).

---

## Docker

O projeto possui **dois níveis de execução**:

### Modo desenvolvimento — `docker-compose.yml`

Define três serviços não-restritivos (focados em produtividade no desenvolvimento):

1. **db** (`mysql:8.4`) — persiste em volume `db_data`, porta `3306` exposta no host, healthcheck de ping.
2. **backend** — build local, depende do banco saudável, monta `./backend` em `/app` (Uvicorn com reload) e expõe a porta `8000`.
3. **frontend** — Vite dev server (HMR), monta `./frontend` em `/app` com `node_modules` em volume separado, expõe a porta `5173` e faz proxy de `/api` para o backend.

### Modo produção — `docker-compose.prod.yml` (+ `frontend/Dockerfile.prod` e `backend/Dockerfile.prod`)

1. **db** (`mysql:8.4`) — volume `db_data`, **sem porta exposta** (apenas rede interna).
2. **backend** — imagem multi-worker com **usuário não-root** e **sem volume de código** (build imutável); só alcançável pela rede interna.
3. **frontend** — multi-stage: build no Node e servido pelo **nginx**, expondo somente a porta do host (`FRONTEND_PORT`, padrão `80`). O nginx adiciona **headers de segurança** (CSP, `nosniff`, `X-Frame-Options`, etc.) e faz proxy de `/api` para o backend.

Ambos os modos usam `restart: unless-stopped` e os dados do MySQL ficam no volume `db_data`.