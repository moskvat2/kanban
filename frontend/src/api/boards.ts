import { api } from "./client";
import type { Board, BoardMember, BoardRole, BoardSummary, Card, TokenResponse, User } from "../types";

export const authApi = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post<TokenResponse>("/auth/register", data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", data).then((r) => r.data),

  me: () => api.get<User>("/auth/me").then((r) => r.data),
};

export const boardsApi = {
  list: () => api.get<BoardSummary[]>("/boards").then((r) => r.data),

  get: (id: number) => api.get<Board>(`/boards/${id}`).then((r) => r.data),

  create: (data: { title: string; description?: string }) =>
    api.post<BoardSummary>("/boards", data).then((r) => r.data),

  update: (id: number, data: { title?: string; description?: string }) =>
    api.patch<BoardSummary>(`/boards/${id}`, data).then((r) => r.data),

  remove: (id: number) => api.delete(`/boards/${id}`),

  createColumn: (boardId: number, title: string) =>
    api.post<Board>(`/boards/${boardId}/columns`, { title }).then((r) => r.data),

  updateColumn: (columnId: number, title: string) =>
    api.patch<Board>(`/boards/columns/${columnId}`, { title }).then((r) => r.data),

  removeColumn: (columnId: number) => api.delete(`/boards/columns/${columnId}`),

  reorderColumns: (boardId: number, items: { id: number; position: number }[]) =>
    api.patch<Board>(`/boards/${boardId}/columns/reorder`, items).then((r) => r.data),
};

export const membersApi = {
  list: (boardId: number) =>
    api.get<BoardMember[]>(`/boards/${boardId}/members`).then((r) => r.data),

  add: (boardId: number, data: { email: string; role: BoardRole }) =>
    api.post<BoardMember>(`/boards/${boardId}/members`, data).then((r) => r.data),

  updateRole: (boardId: number, userId: number, role: BoardRole) =>
    api.patch<BoardMember>(`/boards/${boardId}/members/${userId}`, { role }).then((r) => r.data),

  remove: (boardId: number, userId: number) =>
    api.delete(`/boards/${boardId}/members/${userId}`),
};

export const cardsApi = {
  create: (columnId: number, data: { title: string; description?: string }) =>
    api.post<Board>(`/columns/${columnId}/cards`, data).then((r) => r.data),

  update: (cardId: number, data: { title?: string; description?: string }) =>
    api.patch<Card>(`/cards/${cardId}`, data).then((r) => r.data),

  remove: (cardId: number) => api.delete(`/cards/${cardId}`),

  move: (cardId: number, columnId: number, position: number) =>
    api.post<Board>(`/cards/${cardId}/move`, { column_id: columnId, position }).then((r) => r.data),
};
