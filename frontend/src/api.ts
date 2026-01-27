import type {
  CompareResponse,
  FeedbackResponse,
  TranscriptionResponse,
} from './types/api';

export type ApiClientOptions = {
  baseUrl?: string;
};

export type TranscribeRequest = {
  audio: File | Blob;
  lang?: string;
};

export type CompareRequest = {
  audio: File | Blob;
  text: string;
  lang?: string;
  mode?: 'casual' | 'objective' | 'phonetic';
  evaluationLevel?: 'phonemic' | 'phonetic';
};

export type FeedbackRequest = {
  audio: File | Blob;
  text: string;
  lang?: string;
  mode?: 'casual' | 'objective' | 'phonetic';
  evaluationLevel?: 'phonemic' | 'phonetic';
  feedbackLevel?: 'casual' | 'precise';
  persist?: boolean;
  modelPack?: string;
  llm?: string;
  promptPath?: string;
  outputSchemaPath?: string;
};

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = normalizeBase(options.baseUrl ?? defaultBaseUrl());

  return {
    async transcribe(payload: TranscribeRequest): Promise<TranscriptionResponse> {
      const form = new FormData();
      form.append('audio', payload.audio);
      form.append('lang', payload.lang ?? 'es');
      return postForm<TranscriptionResponse>(`${baseUrl}/v1/transcribe`, form);
    },

    async compare(payload: CompareRequest): Promise<CompareResponse> {
      const form = new FormData();
      form.append('audio', payload.audio);
      form.append('text', payload.text);
      form.append('lang', payload.lang ?? 'es');
      form.append('mode', payload.mode ?? 'objective');
      form.append('evaluation_level', payload.evaluationLevel ?? 'phonemic');
      return postForm<CompareResponse>(`${baseUrl}/v1/compare`, form);
    },

    async feedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
      const form = new FormData();
      form.append('audio', payload.audio);
      form.append('text', payload.text);
      form.append('lang', payload.lang ?? 'es');
      if (payload.mode) {
        form.append('mode', payload.mode);
      }
      if (payload.evaluationLevel) {
        form.append('evaluation_level', payload.evaluationLevel);
      }
      if (payload.feedbackLevel) {
        form.append('feedback_level', payload.feedbackLevel);
      }
      if (payload.persist) {
        form.append('persist', 'true');
      }
      if (payload.modelPack) {
        form.append('model_pack', payload.modelPack);
      }
      if (payload.llm) {
        form.append('llm', payload.llm);
      }
      if (payload.promptPath) {
        form.append('prompt_path', payload.promptPath);
      }
      if (payload.outputSchemaPath) {
        form.append('output_schema_path', payload.outputSchemaPath);
      }
      return postForm<FeedbackResponse>(`${baseUrl}/v1/feedback`, form);
    },
  };
}

function normalizeBase(baseUrl: string): string {
  return baseUrl.replace(/\/$/, '');
}

function defaultBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const win = window as typeof window & { PRONUNCIAPA_API_BASE?: string };
    return win.PRONUNCIAPA_API_BASE ?? document.body?.dataset?.apiBase ?? 'http://localhost:8000';
  }
  return 'http://localhost:8000';
}

async function postForm<T>(url: string, form: FormData): Promise<T> {
  const response = await fetch(url, { method: 'POST', body: form });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        message = payload.detail;
      }
    } catch (_err) {
      // noop
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
