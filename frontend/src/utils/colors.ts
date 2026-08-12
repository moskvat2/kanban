export const ACCENT_COLORS = [
  "#6366f1",
  "#8b5cf6",
  "#ec4899",
  "#f59e0b",
  "#10b981",
  "#06b6d4",
  "#f43f5e",
  "#84cc16",
];

export function accentFor(id: number): string {
  return ACCENT_COLORS[Math.abs(id) % ACCENT_COLORS.length];
}
