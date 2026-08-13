import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  DragDropContext,
  Draggable,
  Droppable,
  type DropResult,
} from "@hello-pangea/dnd";
import { boardsApi, cardsApi, membersApi } from "../api/boards";
import { getToken } from "../api/client";
import { Topbar } from "../components/Topbar";
import type { Board, BoardMember, BoardRole, Card, Column } from "../types";
import { accentFor } from "../utils/colors";

export function BoardPage() {
  const { id } = useParams<{ id: string }>();
  const boardId = Number(id);
  const navigate = useNavigate();

  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [addingColumn, setAddingColumn] = useState(false);
  const [newColumnTitle, setNewColumnTitle] = useState("");

  const [editingColumn, setEditingColumn] = useState<number | null>(null);
  const [columnTitleDraft, setColumnTitleDraft] = useState("");

  const [addingCardIn, setAddingCardIn] = useState<number | null>(null);
  const [cardDraft, setCardDraft] = useState("");

  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [cardTitleDraft, setCardTitleDraft] = useState("");
  const [cardDescDraft, setCardDescDraft] = useState("");
  const [moveTargetColumnId, setMoveTargetColumnId] = useState<number | null>(null);

  const [membersOpen, setMembersOpen] = useState(false);
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<BoardRole>("editor");

  const canvasRef = useRef<HTMLElement | null>(null);
  const [stackColumns, setStackColumns] = useState(false);

  useEffect(() => {
    function updateStacking() {
      const width = window.innerWidth;
      const colWidth = width <= 480 ? 270 : 300;
      const gap = width <= 480 ? 12 : 16;
      const horizontalPadding = width <= 480 ? 24 : 48;
      const columns = board?.columns ?? [];
      const total =
        horizontalPadding +
        columns.length * colWidth +
        (columns.length > 0 ? (columns.length - 1) * gap : 0);
      setStackColumns(total > width);
    }
    updateStacking();
    window.addEventListener("resize", updateStacking);
    return () => window.removeEventListener("resize", updateStacking);
  }, [board]);

  const loadBoard = useCallback(async () => {
    try {
      const data = await boardsApi.get(boardId);
      setBoard(data);
    } catch {
      setError("Não foi possível carregar o quadro.");
    } finally {
      setLoading(false);
    }
  }, [boardId]);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  useEffect(() => {
    if (!boardId) return;
    let disposed = false;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let attempt = 0;

    function handleMessage(event: MessageEvent) {
      let msg: { type?: string; board?: Board; members?: BoardMember[] };
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.type === "board_update" && msg.board) {
        setBoard(msg.board);
      } else if (msg.type === "members_update" && msg.members) {
        setMembers(msg.members);
      } else if (msg.type === "board_deleted") {
        navigate("/");
      }
    }

    function connect() {
      if (disposed) return;
      const token = getToken();
      if (!token) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${protocol}://${window.location.host}/ws/board/${boardId}?token=${encodeURIComponent(token)}`,
      );
      socket.onopen = () => {
        attempt = 0;
      };
      socket.onmessage = handleMessage;
      socket.onclose = () => {
        socket = null;
        if (disposed) return;
        attempt += 1;
        retryTimer = window.setTimeout(connect, Math.min(3000 * 2 ** (attempt - 1), 15000));
      };
    }

    connect();
    return () => {
      disposed = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [boardId, navigate]);

  const canEdit = board ? board.role !== "viewer" : false;

  async function openMembers() {
    if (!board) return;
    setMembersOpen(true);
    setMembersError(null);
    try {
      const data = await membersApi.list(board.id);
      setMembers(data);
    } catch {
      setMembersError("Não foi possível carregar os membros.");
    }
  }

  async function handleAddMember(event: FormEvent) {
    event.preventDefault();
    if (!board || !newMemberEmail.trim()) return;
    try {
      const member = await membersApi.add(board.id, {
        email: newMemberEmail.trim(),
        role: newMemberRole,
      });
      setMembers((prev) => [...prev, member]);
      setNewMemberEmail("");
      setNewMemberRole("editor");
    } catch {
      setMembersError("Não foi possível adicionar o membro. Verifique o e-mail.");
    }
  }

  async function handleChangeRole(member: BoardMember, role: BoardRole) {
    if (!board) return;
    try {
      const updated = await membersApi.updateRole(board.id, member.user_id, role);
      setMembers((prev) => prev.map((m) => (m.user_id === updated.user_id ? updated : m)));
    } catch {
      setMembersError("Não foi possível alterar o papel.");
    }
  }

  async function handleRemoveMember(member: BoardMember) {
    if (!board) return;
    if (!window.confirm(`Remover "${member.name}" do quadro?`)) return;
    try {
      await membersApi.remove(board.id, member.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== member.user_id));
    } catch {
      setMembersError("Não foi possível remover o membro.");
    }
  }

  function onDragEnd(result: DropResult) {
    const { destination, source, type } = result;
    if (!canEdit) return;
    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) {
      return;
    }

    if (type === "COLUMN") {
      const prev = board;
      if (!prev) return;
      const next = applyColumnMove(prev, source.index, destination.index);
      setBoard(next);
      void boardsApi
        .reorderColumns(boardId, next.columns.map((c) => ({ id: c.id, position: c.position })))
        .catch(() => void loadBoard());
      return;
    }

    if (type === "CARD") {
      const prev = board;
      if (!prev) return;
      const cardId = Number(result.draggableId.replace("card-", ""));
      const sourceColId = Number(source.droppableId);
      const destColId = Number(destination.droppableId);
      const next = applyCardMove(prev, cardId, sourceColId, destColId, destination.index);
      setBoard(next);
      void cardsApi
        .move(cardId, destColId, destination.index)
        .then(setBoard)
        .catch(() => void loadBoard());
    }
  }

  async function handleCreateColumn() {
    const title = newColumnTitle.trim();
    if (!title) return;
    try {
      const updated = await boardsApi.createColumn(boardId, title);
      setBoard(updated);
      setNewColumnTitle("");
      setAddingColumn(false);
    } catch {
      setError("Não foi possível criar a coluna.");
    }
  }

  async function handleRenameColumn(column: Column) {
    const title = columnTitleDraft.trim();
    if (!title || title === column.title) {
      setEditingColumn(null);
      return;
    }
    try {
      const updated = await boardsApi.updateColumn(column.id, title);
      setBoard(updated);
    } catch {
      setError("Não foi possível renomear a coluna.");
    }
    setEditingColumn(null);
  }

  async function handleDeleteColumn(column: Column) {
    if (!window.confirm(`Excluir a coluna "${column.title}" e todos os cartões?`)) return;
    try {
      await boardsApi.removeColumn(column.id);
      setBoard((prev) => (prev ? { ...prev, columns: prev.columns.filter((c) => c.id !== column.id) } : prev));
    } catch {
      setError("Não foi possível excluir a coluna.");
    }
  }

  async function handleCreateCard(column: Column) {
    const title = cardDraft.trim();
    if (!title) return;
    try {
      const updated = await cardsApi.create(column.id, { title });
      setBoard(updated);
      setCardDraft("");
      setAddingCardIn(null);
    } catch {
      setError("Não foi possível criar o cartão.");
    }
  }

  async function handleUpdateCard() {
    if (!selectedCard) return;
    const title = cardTitleDraft.trim();
    if (!title) {
      setSelectedCard(null);
      return;
    }
    try {
      const updated = await cardsApi.update(selectedCard.id, {
        title,
        description: cardDescDraft.trim() || undefined,
      });
      setBoard((prev) =>
        prev
          ? {
              ...prev,
              columns: prev.columns.map((c) =>
                c.id === selectedCard.column_id
                  ? { ...c, cards: c.cards.map((card) => (card.id === updated.id ? updated : card)) }
                  : c,
              ),
            }
          : prev,
      );
      setSelectedCard(null);
    } catch {
      setError("Não foi possível salvar o cartão.");
    }
  }

  async function handleDeleteCard() {
    if (!selectedCard) return;
    try {
      await cardsApi.remove(selectedCard.id);
      setBoard((prev) =>
        prev
          ? {
              ...prev,
              columns: prev.columns.map((c) =>
                c.id === selectedCard.column_id
                  ? { ...c, cards: c.cards.filter((card) => card.id !== selectedCard.id) }
                  : c,
              ),
            }
          : prev,
      );
      setSelectedCard(null);
    } catch {
      setError("Não foi possível excluir o cartão.");
    }
  }

  async function handleMoveCard() {
    if (!selectedCard || !board) return;
    const targetColumnId = moveTargetColumnId;
    if (targetColumnId === null || targetColumnId === selectedCard.column_id) return;
    const targetColumn = board.columns.find((c) => c.id === targetColumnId);
    if (!targetColumn) return;
    try {
      const updated = await cardsApi.move(
        selectedCard.id,
        targetColumnId,
        targetColumn.cards.length,
      );
      setBoard(updated);
      setSelectedCard(null);
      setMoveTargetColumnId(null);
    } catch {
      setError("Não foi possível mover o cartão.");
    }
  }

  if (loading) {
    return (
      <div className="screen-center">
        <div className="loading-spinner" />
        <p className="empty-state">Carregando quadro...</p>
      </div>
    );
  }

  if (!board) {
    return (
      <div className="screen-center">
        <p className="form-error">{error ?? "Quadro não encontrado."}</p>
        <button className="btn-ghost" onClick={() => navigate("/")}>
          Voltar
        </button>
      </div>
    );
  }

  return (
    <div className="board-page">
      <Topbar
        title={board.title}
        actions={
          <>
            {error && <span className="inline-error">{error}</span>}
            <button
              type="button"
              className="btn-ghost"
              onClick={() => void openMembers()}
            >
              Compartilhar
            </button>
            {canEdit && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  setAddingColumn(true);
                }}
              >
                + Coluna
              </button>
            )}
          </>
        }
      />

      <DragDropContext onDragEnd={onDragEnd}>
        <Droppable droppableId="board" direction="horizontal" type="COLUMN">
          {(provided) => (
            <main
              className={`board-canvas${stackColumns ? " stacked" : ""}`}
              ref={(node) => {
                canvasRef.current = node;
                provided.innerRef(node);
              }}
              {...provided.droppableProps}
            >
              {board.columns.map((column, columnIndex) => (
                <Draggable
                  key={column.id}
                  draggableId={String(column.id)}
                  index={columnIndex}
                  isDragDisabled={!canEdit}
                >
                  {(colProvided, colSnapshot) => (
                    <section
                      className={`board-column ${colSnapshot.isDragging ? "dragging" : ""}`}
                      ref={colProvided.innerRef}
                      {...colProvided.draggableProps}
                      style={
                        {
                          ...colProvided.draggableProps.style,
                          "--col-accent": accentFor(column.id),
                        } as unknown as CSSProperties
                      }
                    >
                      <header className="column-header" {...colProvided.dragHandleProps}>
                        {editingColumn === column.id ? (
                          <input
                            autoFocus
                            className="column-title-input"
                            value={columnTitleDraft}
                            onChange={(e) => setColumnTitleDraft(e.target.value)}
                            onBlur={() => void handleRenameColumn(column)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") void handleRenameColumn(column);
                              if (e.key === "Escape") setEditingColumn(null);
                            }}
                          />
                        ) : (
                          <h3
                            className="column-title"
                            onDoubleClick={() => {
                              setEditingColumn(column.id);
                              setColumnTitleDraft(column.title);
                            }}
                          >
                            {column.title}
                            <span className="card-count">{column.cards.length}</span>
                          </h3>
                        )}
                        {canEdit && (
                          <div className="column-actions">
                            <button
                              type="button"
                              title="Renomear"
                              onClick={() => {
                                setEditingColumn(column.id);
                                setColumnTitleDraft(column.title);
                              }}
                            >
                              ✎
                            </button>
                            <button
                              type="button"
                              title="Excluir"
                              onClick={() => void handleDeleteColumn(column)}
                            >
                              ✕
                            </button>
                          </div>
                        )}
                      </header>

                      <Droppable droppableId={String(column.id)} type="CARD">
                        {(cardProvided, cardSnapshot) => (
                          <div
                            className={`card-list ${cardSnapshot.isDraggingOver ? "dragging-over" : ""}`}
                            ref={cardProvided.innerRef}
                            {...cardProvided.droppableProps}
                          >
                            {column.cards.map((card, cardIndex) => (
                              <Draggable
                                key={card.id}
                                draggableId={`card-${card.id}`}
                                index={cardIndex}
                                isDragDisabled={!canEdit}
                              >
                                {(cardDragProvided, cardDragSnapshot) => (
                                  <article
                                    className={`task-card ${cardDragSnapshot.isDragging ? "dragging" : ""}`}
                                    ref={cardDragProvided.innerRef}
                                    {...cardDragProvided.draggableProps}
                                    {...cardDragProvided.dragHandleProps}
                                    onClick={() => {
                                      setSelectedCard(card);
                                      setCardTitleDraft(card.title);
                                      setCardDescDraft(card.description ?? "");
                                      setMoveTargetColumnId(card.column_id);
                                    }}
                                  >
                                    <h4>{card.title}</h4>
                                    {card.description && (
                                      <p className="task-card-desc">{card.description}</p>
                                    )}
                                  </article>
                                )}
                              </Draggable>
                            ))}
                            {cardProvided.placeholder}

                            {addingCardIn === column.id ? (
                              <form
                                className="inline-form"
                                onSubmit={(e) => {
                                  e.preventDefault();
                                  void handleCreateCard(column);
                                }}
                              >
                                <input
                                  autoFocus
                                  type="text"
                                  placeholder="Título do cartão"
                                  value={cardDraft}
                                  onChange={(e) => setCardDraft(e.target.value)}
                                />
                                <div className="form-actions">
                                  <button type="submit" className="btn-primary">
                                    Adicionar
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                      setAddingCardIn(null);
                                      setCardDraft("");
                                    }}
                                  >
                                    Cancelar
                                  </button>
                                </div>
                              </form>
                            ) : canEdit ? (
                              <button
                                type="button"
                                className="add-card-btn"
                                onClick={() => {
                                  setAddingCardIn(column.id);
                                  setCardDraft("");
                                }}
                              >
                                + Adicionar cartão
                              </button>
                            ) : null}
                          </div>
                        )}
                      </Droppable>
                    </section>
                  )}
                </Draggable>
              ))}

              {canEdit && (
                addingColumn ? (
                  <form
                    className="board-column new-column-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void handleCreateColumn();
                    }}
                  >
                    <input
                      autoFocus
                      type="text"
                      placeholder="Título da coluna"
                      value={newColumnTitle}
                      onChange={(e) => setNewColumnTitle(e.target.value)}
                    />
                    <div className="form-actions">
                      <button type="submit" className="btn-primary">
                        Criar
                      </button>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => {
                          setAddingColumn(false);
                          setNewColumnTitle("");
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    type="button"
                    className="add-column-btn"
                    onClick={() => setAddingColumn(true)}
                  >
                    + Nova coluna
                  </button>
                )
              )}
              {provided.placeholder}
            </main>
          )}
        </Droppable>
      </DragDropContext>

      {selectedCard && (
        <div className="modal-overlay" onClick={() => setSelectedCard(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {!canEdit ? (
              <>
                <h3>{selectedCard.title}</h3>
                <div className="viewer-card-view">
                  {selectedCard.description ? (
                    <p>{selectedCard.description}</p>
                  ) : (
                    <p className="empty-state">Sem descrição</p>
                  )}
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn-primary" onClick={() => setSelectedCard(null)}>
                    Fechar
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3>Detalhes do cartão</h3>
                <div className="field">
                  <label htmlFor="card-title">Título</label>
                  <input
                    id="card-title"
                    type="text"
                    value={cardTitleDraft}
                    onChange={(e) => setCardTitleDraft(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="card-desc">Descrição</label>
                  <textarea
                    id="card-desc"
                    rows={5}
                    value={cardDescDraft}
                    onChange={(e) => setCardDescDraft(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="move-card-to">Mover para</label>
                  <select
                    id="move-card-to"
                    value={moveTargetColumnId ?? selectedCard.column_id}
                    onChange={(e) => setMoveTargetColumnId(Number(e.target.value))}
                    disabled={board.columns.length <= 1}
                  >
                    {board.columns.map((column) => (
                      <option
                        key={column.id}
                        value={column.id}
                        disabled={column.id === selectedCard.column_id}
                      >
                        {column.title}
                        {column.id === selectedCard.column_id ? " (atual)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={
                      !moveTargetColumnId || moveTargetColumnId === selectedCard.column_id
                    }
                    onClick={() => void handleMoveCard()}
                    title="Mover o cartão para a coluna selecionada"
                  >
                    Mover
                  </button>
                  <button type="button" className="btn-primary" onClick={() => void handleUpdateCard()}>
                    Salvar
                  </button>
                  <button type="button" className="btn-danger" onClick={() => void handleDeleteCard()}>
                    Excluir
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => setSelectedCard(null)}>
                    Cancelar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {membersOpen && (
        <div className="modal-overlay" onClick={() => setMembersOpen(false)}>
          <div className="modal member-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Compartilhar quadro</h3>

            {membersError && <p className="form-error">{membersError}</p>}

            {board.is_owner && (
              <form className="member-add-form" onSubmit={(e) => void handleAddMember(e)}>
                <input
                  type="email"
                  placeholder="E-mail do membro"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  required
                />
                <select
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value as BoardRole)}
                >
                  <option value="editor">Editor</option>
                  <option value="viewer">Visualizador</option>
                </select>
                <button type="submit" className="btn-primary" disabled={!newMemberEmail.trim()}>
                  Adicionar
                </button>
              </form>
            )}

            <ul className="member-list">
              {members.map((member) => (
                <li key={member.user_id} className="member-item">
                  <span className="member-avatar">{member.name.slice(0, 2).toUpperCase()}</span>
                  <div className="member-info">
                    <span className="member-name">
                      {member.name}
                      {member.user_id === board.owner_id && <em> (dono)</em>}
                    </span>
                    <span className="member-email">{member.email}</span>
                  </div>
                  {board.is_owner && member.role !== "owner" ? (
                    <>
                      <select
                        className="member-role-select"
                        value={member.role}
                        onChange={(e) => void handleChangeRole(member, e.target.value as BoardRole)}
                      >
                        <option value="editor">Editor</option>
                        <option value="viewer">Visualizador</option>
                      </select>
                      <button
                        type="button"
                        className="member-remove-btn"
                        title="Remover do quadro"
                        onClick={() => void handleRemoveMember(member)}
                      >
                        ✕
                      </button>
                    </>
                  ) : (
                    <span className={`member-role-pill ${member.role}`}>
                      {member.role === "owner" ? "Dono" : member.role === "editor" ? "Editor" : "Visualizador"}
                    </span>
                  )}
                </li>
              ))}
            </ul>

            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={() => setMembersOpen(false)}>
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function applyColumnMove(prev: Board, from: number, to: number): Board {
  const columns = [...prev.columns];
  const [moved] = columns.splice(from, 1);
  columns.splice(to, 0, moved);
  columns.forEach((c, index) => (c.position = index));
  return { ...prev, columns };
}

function applyCardMove(
  prev: Board,
  cardId: number,
  sourceColId: number,
  destColId: number,
  destIndex: number,
): Board {
  const columns = prev.columns.map((c) => ({ ...c, cards: [...c.cards] }));
  const sourceCol = columns.find((c) => c.id === sourceColId)!;
  const cardIndex = sourceCol.cards.findIndex((c) => c.id === cardId);
  const [moved] = sourceCol.cards.splice(cardIndex, 1);
  const relocated = { ...moved, column_id: destColId };

  if (sourceColId === destColId) {
    sourceCol.cards.splice(destIndex, 0, relocated);
    sourceCol.cards.forEach((c, index) => (c.position = index));
  } else {
    const destCol = columns.find((c) => c.id === destColId)!;
    destCol.cards.splice(destIndex, 0, relocated);
    sourceCol.cards.forEach((c, index) => (c.position = index));
    destCol.cards.forEach((c, index) => (c.position = index));
  }
  return { ...prev, columns };
}
