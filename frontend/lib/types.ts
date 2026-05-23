export interface ChatRequest {
  message: string;
  k?: number;
}

export interface SourceInfo {
  title: string;
  file_path: string;
  chunk_index: number;
  distance: number | null;
}

export interface ChatResponse {
  answer: string;
  sources: SourceInfo[];
  model: string;
}
