// Shapes from ADR 0006.
export type Hit = { doc_id: string; source: string; chunk_index: number; score: number; passed: boolean; text: string };
export type Finding = { entity_type: string; placeholder: string };
export type Source = { doc_id: string; source: string; chunk_index: number };
export type QueryResponse = {
  answer: string; refused: boolean; sources: Source[];
  trace: { hits: Hit[]; findings_in: Finding[]; findings_out: Finding[] };
};
export type IngestStatus = "pending" | "ready" | "failed";
export type Doc = { doc_id: string; filename: string; status: IngestStatus; chunks: number | null };
export const MIN_SCORE = 0.7;
