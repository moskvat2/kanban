export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Card {
  id: number;
  column_id: number;
  title: string;
  description: string | null;
  position: number;
  created_at: string;
}

export interface Column {
  id: number;
  board_id: number;
  title: string;
  position: number;
  created_at: string;
  cards: Card[];
}

export interface Board {
  id: number;
  title: string;
  description: string | null;
  owner_id: number;
  created_at: string;
  columns: Column[];
}

export interface BoardSummary {
  id: number;
  title: string;
  description: string | null;
  owner_id: number;
  created_at: string;
  progress: number;
  cards_count: number;
  done_cards: number;
  columns_count: number;
}
