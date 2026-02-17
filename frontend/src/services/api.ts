/**
 * PronunciaPA API client service
 */
import type {
  CompareResponse,
  FeedbackResponse,
  TranscriptionResponse,
  HealthResponse,
  CompareMode,
  TranscriptionMode,
  FeedbackLevel,
  LearningOverview,
  SoundLesson,
} from '@/types';

const getBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    return (
      (window as any).PRONUNCIAPA_API_BASE ??
      document.body?.dataset?.apiBase ??
      ''
    );
  }
  return '';
};

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const base = getBaseUrl();
  const res = await fetch(`${base}${url}`, init);
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(
      `API error ${res.status}: ${detail}`,
      res.status,
      detail,
    );
  }
  return res.json() as Promise<T>;
}

export interface TranscribeParams {
  audio: Blob;
  lang: string;
  userId?: string;
}

export interface CompareParams {
  audio: Blob;
  text: string;
  lang: string;
  mode?: CompareMode;
  evaluationLevel?: TranscriptionMode;
  userId?: string;
}

export interface FeedbackParams extends CompareParams {
  feedbackLevel?: FeedbackLevel;
}

function buildForm(params: Record<string, unknown>): FormData {
  const fd = new FormData();
  for (const [key, val] of Object.entries(params)) {
    if (val === undefined || val === null) continue;
    if (val instanceof Blob) {
      fd.append(key, val, 'recording.webm');
    } else {
      fd.append(key, String(val));
    }
  }
  return fd;
}

export const api = {
  async checkHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },

  async getLearningOverview(lang: string): Promise<LearningOverview> {
    return request<LearningOverview>(`/api/ipa-learn/${lang}`);
  },

  async getSoundLesson(
    lang: string,
    soundId: string,
    options?: { includeAudio?: boolean; maxDrills?: number; generate?: boolean },
  ): Promise<SoundLesson> {
    const params = new URLSearchParams();
    if (options?.includeAudio !== undefined) {
      params.set('include_audio', String(options.includeAudio));
    }
    if (options?.maxDrills !== undefined) {
      params.set('max_drills', String(options.maxDrills));
    }
    if (options?.generate !== undefined) {
      params.set('generate', String(options.generate));
    }
    const query = params.toString();
    const path = `/api/ipa-lesson/${lang}/${encodeURIComponent(soundId)}`;
    return request<SoundLesson>(query ? `${path}?${query}` : path);
  },

  async transcribe(params: TranscribeParams): Promise<TranscriptionResponse> {
    const fd = buildForm({
      audio: params.audio,
      lang: params.lang,
      user_id: params.userId,
    });
    return request<TranscriptionResponse>('/v1/transcribe', {
      method: 'POST',
      body: fd,
    });
  },

  async compare(params: CompareParams): Promise<CompareResponse> {
    const fd = buildForm({
      audio: params.audio,
      text: params.text,
      lang: params.lang,
      mode: params.mode ?? 'objective',
      evaluation_level: params.evaluationLevel ?? 'phonemic',
      user_id: params.userId,
    });
    return request<CompareResponse>('/v1/compare', {
      method: 'POST',
      body: fd,
    });
  },

  async feedback(params: FeedbackParams): Promise<FeedbackResponse> {
    const fd = buildForm({
      audio: params.audio,
      text: params.text,
      lang: params.lang,
      mode: params.mode ?? 'objective',
      evaluation_level: params.evaluationLevel ?? 'phonemic',
      feedback_level: params.feedbackLevel ?? 'casual',
      user_id: params.userId,
    });
    return request<FeedbackResponse>('/v1/feedback', {
      method: 'POST',
      body: fd,
    });
  },
};

export { ApiError };
export default api;
