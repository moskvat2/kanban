import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { boardsApi } from "../api/boards";
import { Topbar } from "../components/Topbar";
import type { BoardSummary } from "../types";
import { accentFor } from "../utils/colors";

export function Dashboard() {
  const navigate = useNavigate();

  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  const loadBoards = useCallback(async () => {
    try {
      const data = await boardsApi.list();
      setBoards(data);
    } catch {
      setError("Não foi possível carregar seus quadros.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const board = await boardsApi.create({ title: newTitle.trim(), description: newDescription.trim() || undefined });
      setNewTitle("");
      setNewDescription("");
      setCreating(false);
      navigate(`/board/${board.id}`);
    } catch {
      setError("Não foi possível criar o quadro.");
    }
  }

  async function handleDelete(boardId: number) {
    if (!window.confirm("Excluir este quadro e todo o seu conteúdo?")) return;
    try {
      await boardsApi.remove(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch {
      setError("Não foi possível excluir o quadro.");
    }
  }

  return (
    <div className="dashboard">
      <Topbar title="Meus quadros" />

      <main className="dashboard-main">
        {error && <p className="form-error">{error}</p>}

        {loading ? (
          <div className="screen-center">
            <div className="loading-spinner" />
            <p className="empty-state">Carregando seus quadros...</p>
          </div>
        ) : (
          <div className="board-grid">
          {!creating && (
            <button
              type="button"
              className="board-card new-board"
              onClick={() => setCreating(true)}
            >
              <span className="new-board-plus">+</span>
              <span>Novo quadro</span>
            </button>
          )}

          {creating && (
            <form className="board-card new-board-form" onSubmit={handleCreate}>
              <input
                autoFocus
                type="text"
                placeholder="Título do quadro"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                required
              />
              <input
                type="text"
                placeholder="Descrição (opcional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={!newTitle.trim()}>
                  Criar
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setCreating(false);
                    setNewTitle("");
                    setNewDescription("");
                  }}
                >
                  Cancelar
                </button>
              </div>
            </form>
          )}

          {boards.map((board) => (
            <div
              key={board.id}
              className="board-card"
              role="button"
              tabIndex={0}
              style={{ "--card-accent": accentFor(board.id) } as CSSProperties}
              onClick={() => navigate(`/board/${board.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/board/${board.id}`);
              }}
            >
              <h3>{board.title}</h3>
              <span className={`board-role-badge${board.is_owner ? "" : " shared"}`}>
                {board.is_owner ? "Dono" : "Compartilhado"}
              </span>
              {board.description && <p className="board-desc">{board.description}</p>}
              <div className="board-progress">
                <div className="board-progress-head">
                  <span>Andamento</span>
                  <span className="board-progress-pct">
                    {board.cards_count === 0 ? "—" : `${Math.round(board.progress * 100)}%`}
                  </span>
                </div>
                <div className="board-progress-track">
                  <div
                    className="board-progress-fill"
                    style={{ width: `${Math.round(board.progress * 100)}%` }}
                  />
                </div>
                <span className="board-progress-meta">
                  {board.cards_count === 0
                    ? "Sem cartões ainda"
                    : `${board.done_cards} de ${board.cards_count} concluído${board.done_cards === 1 ? "" : "s"}`}
                </span>
              </div>
              {board.is_owner && (
                <button
                  type="button"
                  className="delete-board"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleDelete(board.id);
                  }}
                  title="Excluir quadro"
                >
                  Excluir
                </button>
              )}
            </div>
          ))}
          </div>
        )}

        {!loading && boards.length === 0 && !creating && (
          <div className="empty-state">
            <div className="empty-state-icon">▦</div>
            <p>Você ainda não tem quadros. Crie o seu primeiro!</p>
          </div>
        )}
      </main>
    </div>
  );
}
