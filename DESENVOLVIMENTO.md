# Fluxo de Desenvolvimento e Processo do Sistema

Documento que registra o processo de desenvolvimento do **Sistema Kanban**, o estado atual e o histórico das funcionalidades até o momento.

---

## 1. Contexto geral

Sistema de quadro Kanban composto por:

- **Frontend:** React 18 + Vite + TypeScript, react-router-dom, @hello-pangea/dnd (drag & drop), Axios.
- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2, JWT (PyJWT) e bcrypt.
- **Banco de dados:** MySQL 8.4.
- **Infraestrutura:** Docker Compose (serviços `db`, `backend`, `frontend`).

A aplicação roda em **http://localhost:5173** (frontend) e **http://localhost:8000** (backend / Swagger em `/docs`).

---

## 2. Etapas de desenvolvimento (até o momento)

### 2.1 Estruturação do projeto
- Criação do monorepo com `backend/`, `frontend/`, `docker-compose.yml` e `.env.example`.
- Desenho dos modelos de dados: `User`, `Board`, `Column`, `Card`.
- Definição da API REST e do fluxo de autenticação.

### 2.2 Autenticação JWT
- Registro e login de usuários (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`).
- Senhas com hash `bcrypt` e tokens JWT com expiração configurável.
- Autorização por proprietário: cada usuário acessa apenas os próprios quadros (404/403).

### 2.3 CRUD de quadros, colunas e cartões
- Criação, listagem, atualização e exclusão de quadros.
- Criação, renomeação e exclusão de colunas, com reordenação automática por `position`.
- Criação, edição, exclusão e movimentação de cartões.

### 2.4 Drag & drop
- Arrastar cartões entre colunas e reordenar colunas usando `@hello-pangea/dnd`.
- Atualização otimista da interface com sincronização via API e recarga em caso de erro.

### 2.5 Correções na movimentação de tarefas
- **Bug de lógica (frontend):** ao mover cartão dentro da mesma coluna, a remoção e o re-insert eram feitos em cópias diferentes do array — cartão duplicava. Corrigido tratando a movimentação mesma-coluna como caso especial.
- **Bug de drag & drop (CSS):**
  - Animações com `transform` + `animation-fill-mode: both` sobrescreviam o `transform` inline da biblioteca (cartão “pulava” em direção aleatória) → trocadas por animação apenas de `opacity`.
  - `backdrop-filter` no ancestral criava *containing block* e quebrava o `position: fixed` usado durante o arrasto → removido.

### 2.6 Barra superior (Topbar)
- Componente reutilizável com logotipo, menu de navegação, título da página e menu do usuário ativo (avatar com iniciais, nome, e-mail e logout).

### 2.7 Andamento do projeto (progresso)
- O dashboard mostra uma barra de progresso para cada quadro.
- **Lógica:** `progresso = cartões na última coluna / total de cartões`. Ex.: 4 cartões, 1 concluído → `25%`.
- O resumo também entrega `cards_count`, `done_cards` e `columns_count`.

### 2.8 Temas claro e escuro
- Contexto `ThemeContext` que persiste a escolha em `localStorage` e aplica `data-theme` no `<html>`.
- Seleção **☀ claro / ☾ escuro** na barra superior (respeita `prefers-color-scheme` como padrão).
- Paleta refatorada em variáveis CSS semânticas para alternar entre os temas (inclusive texto do logotipo).

### 2.9 Responsividade mobile
- Media queries em `global.css` para mobile (topbar compacta, cards de quadro menores, modal com scroll, toque).
- **Empilhamento vertical:** quando a largura total das colunas excede a largura da tela, o board passa de rolagem horizontal para colunas empilhadas na vertical (cálculo dinâmico por quantidade de colunas).

### 2.10 Mover tarefa para outro nível
- No modal do cartão, seletor **“Mover para”** permite enviar a tarefa para outra coluna (ex.: “novo” → “execução”).
- Funciona por toque (mobile) e mouse (desktop), complementando o drag & drop.

### 2.11 Controle de versão
- Repositório Git inicializado com branch `main` e depois branch `Developer` (atual).
- Publicação no GitHub via SSH (`git@github.com:moskvat2/kanban.git`).

### 2.12 Ambientes dev/produção e segurança
- **Dois níveis de execução via Docker Compose:**
  - `docker-compose.yml` — desenvolvimento (relaxado: reload, volumes, portas expostas).
  - `docker-compose.prod.yml` — produção (seguro: banco/backend sem porta exposta, backend com usuário não-root, frontend estático no nginx).
- **Nginx de produção:** headers de segurança (CSP, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`) e proxy `/api` para o backend.
- **Backend:** middleware de security headers e `react-router-dom` atualizado para a correção mais recente da série 6 (`6.30.4`).
- Criação de `package-lock.json` para builds reproduzíveis (`npm ci`).

---

## 3. Processo de trabalho

Para cada funcionalidade seguimos o fluxo:

1. **Entendimento da necessidade** — diálogo sobre o comportamento desejado (ex.: cálculo de progresso, tema, movimentação em mobile).
2. **Implementação** — código no backend (FastAPI) e/ou frontend (React/CSS).
3. **Validação** — `tsc` (typecheck do frontend) e testes manuais/automáticos (ex.: API com `curl` para confirmar o cálculo de progresso).
4. **Revisão** — verificação no navegador (incluindo modo dispositivo para mobile).
5. **Commit e push** — somente após autorização explícita do usuário.

### Comandos úteis

```bash
# subir a aplicação
docker compose up -d --build

# typecheck do frontend (dentro do container)
docker compose exec -T frontend npx tsc -b --noEmit

# logs
docker compose logs backend frontend

# git
git status
git add -A
git commit -m "mensagem"
git push -u origin Developer
```

---

## 4. Estado atual do sistema

**Implementado:**
- Autenticação JWT (registro, login, sessão persistida).
- CRUD completo de quadros, colunas e cartões.
- Drag & drop de cartões e colunas (desktop) + mover via modal (desktop e mobile).
- Reordenação e empilhamento responsivo no mobile.
- Barra de progresso por quadro no dashboard.
- Topbar com logotipo, navegação e menu do usuário.
- Temas claro/escuro configuráveis e persistidos.
- Responsividade mobile.

**Infra:** Docker Compose com MySQL 8.4, backend FastAPI (reload) e frontend Vite (HMR).

---

## 5. Possíveis próximos passos

- Filtro/busca de cartões dentro do quadro.
- Etiquetas e prazos nos cartões.
- Colaboração em tempo real (websockets) ou convites para um mesmo quadro.
- Migrações de banco (Alembic) em vez de `create_all`.
- Testes automatizados (backend `pytest`, frontend com Vitest/RTL).
- CI/CD para build e deploy.