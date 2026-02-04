/**
 * Realtime audio streaming client for PronunciaPA
 * 
 * Connects to WebSocket endpoint for real-time pronunciation feedback.
 * Uses Web Audio API for audio capture and volume visualization.
 * 
 * @example
 * const client = new RealtimeClient({ baseUrl: 'ws://localhost:8000' });
 * client.onState((state) => updateUI(state));
 * client.onTranscription((result) => showResult(result));
 * await client.connect();
 * await client.startRecording();
 */

// ============================================================================
// Types
// ============================================================================

export interface RealtimeConfig {
  /** WebSocket base URL (ws:// or wss://) */
  baseUrl?: string;
  /** Target language for transcription */
  lang?: string;
  /** Reference text for comparison (optional) */
  referenceText?: string;
  /** Comparison mode */
  mode?: 'casual' | 'objective' | 'phonetic' | 'auto';
  /** Evaluation level */
  evaluationLevel?: 'phonemic' | 'phonetic' | 'auto';
  /** Audio chunk interval in milliseconds */
  chunkIntervalMs?: number;
}

export interface StreamState {
  type?: 'state';
  /** Whether voice is currently detected */
  isSpeaking: boolean;
  /** Volume level 0.0 to 1.0 */
  volumeLevel: number;
  /** Current buffer duration in ms */
  bufferDurationMs: number;
  /** Current status: idle, listening, speaking, processing */
  status: 'idle' | 'listening' | 'speaking' | 'processing';
}

export interface TranscriptionResult {
  type: 'transcription';
  ipa: string;
  tokens: string[];
  durationMs: number;
}

export interface ComparisonResult {
  type: 'comparison';
  score: number;
  userIpa: string;
  refIpa: string;
  alignment: Array<{
    ref: string;
    user: string;
    op: 'match' | 'substitute' | 'insert' | 'delete';
  }>;
  durationMs: number;
}

export interface RealtimeError {
  type: 'error';
  message: string;
  code: string;
}

export type RealtimeMessage = 
  | StreamState 
  | TranscriptionResult 
  | ComparisonResult 
  | RealtimeError
  | { type: 'ready'; message: string; config: Record<string, unknown> }
  | { type: 'pong' };

// Callback types
export type StateCallback = (state: StreamState) => void;
export type TranscriptionCallback = (result: TranscriptionResult) => void;
export type ComparisonCallback = (result: ComparisonResult) => void;
export type ErrorCallback = (error: RealtimeError) => void;
export type VolumeCallback = (volume: number) => void;

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_CHUNK_INTERVAL_MS = 200;
const DEFAULT_SAMPLE_RATE = 16000;

// ============================================================================
// RealtimeClient
// ============================================================================

export class RealtimeClient {
  private config: Required<RealtimeConfig>;
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private analyser: AnalyserNode | null = null;
  private isRecording = false;
  private chunkTimer: number | null = null;
  
  // Callbacks
  private onStateCallbacks: StateCallback[] = [];
  private onTranscriptionCallbacks: TranscriptionCallback[] = [];
  private onComparisonCallbacks: ComparisonCallback[] = [];
  private onErrorCallbacks: ErrorCallback[] = [];
  private onVolumeCallbacks: VolumeCallback[] = [];
  private onConnectedCallbacks: Array<() => void> = [];
  private onDisconnectedCallbacks: Array<() => void> = [];

  constructor(config: RealtimeConfig = {}) {
    this.config = {
      baseUrl: config.baseUrl ?? this.getDefaultWsUrl(),
      lang: config.lang ?? 'es',
      referenceText: config.referenceText ?? '',
      mode: config.mode ?? 'objective',
      evaluationLevel: config.evaluationLevel ?? 'phonemic',
      chunkIntervalMs: config.chunkIntervalMs ?? DEFAULT_CHUNK_INTERVAL_MS,
    };
  }

  private getDefaultWsUrl(): string {
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.hostname}:8000`;
    }
    return 'ws://localhost:8000';
  }

  // ============================================================================
  // Public API - Event Registration
  // ============================================================================

  /** Register callback for stream state updates (speaking, volume, etc.) */
  onState(callback: StateCallback): this {
    this.onStateCallbacks.push(callback);
    return this;
  }

  /** Register callback for transcription results */
  onTranscription(callback: TranscriptionCallback): this {
    this.onTranscriptionCallbacks.push(callback);
    return this;
  }

  /** Register callback for comparison results (when reference text is set) */
  onComparison(callback: ComparisonCallback): this {
    this.onComparisonCallbacks.push(callback);
    return this;
  }

  /** Register callback for errors */
  onError(callback: ErrorCallback): this {
    this.onErrorCallbacks.push(callback);
    return this;
  }

  /** Register callback for local volume updates (from Web Audio API) */
  onVolume(callback: VolumeCallback): this {
    this.onVolumeCallbacks.push(callback);
    return this;
  }

  /** Register callback for connection established */
  onConnected(callback: () => void): this {
    this.onConnectedCallbacks.push(callback);
    return this;
  }

  /** Register callback for disconnection */
  onDisconnected(callback: () => void): this {
    this.onDisconnectedCallbacks.push(callback);
    return this;
  }

  // ============================================================================
  // Public API - Connection
  // ============================================================================

  /** Connect to WebSocket server */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    return new Promise((resolve, reject) => {
      const wsUrl = `${this.config.baseUrl}/ws/practice`;
      console.log(`[Realtime] Connecting to ${wsUrl}`);
      
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[Realtime] Connected');
        // Send initial configuration
        this.sendConfig();
        this.onConnectedCallbacks.forEach(cb => cb());
        resolve();
      };

      this.ws.onerror = (event) => {
        console.error('[Realtime] WebSocket error:', event);
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onclose = () => {
        console.log('[Realtime] Disconnected');
        this.onDisconnectedCallbacks.forEach(cb => cb());
        this.cleanup();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };
    });
  }

  /** Disconnect from server */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.cleanup();
  }

  /** Check if connected */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // ============================================================================
  // Public API - Recording
  // ============================================================================

  /** Start audio recording and streaming */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      return;
    }

    if (!this.isConnected) {
      await this.connect();
    }

    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: DEFAULT_SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // Create audio context
      this.audioContext = new AudioContext({ sampleRate: DEFAULT_SAMPLE_RATE });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create analyser for volume visualization
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);

      // Create script processor for audio capture
      // Note: ScriptProcessorNode is deprecated but works reliably across browsers
      // AudioWorklet would be better but has more complex setup
      this.scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
      
      this.scriptProcessor.onaudioprocess = (event) => {
        if (!this.isRecording) return;
        
        const inputData = event.inputBuffer.getChannelData(0);
        const pcmData = this.floatTo16BitPCM(inputData);
        this.sendAudioChunk(pcmData);
      };

      source.connect(this.scriptProcessor);
      this.scriptProcessor.connect(this.audioContext.destination);

      this.isRecording = true;

      // Start volume monitoring
      this.startVolumeMonitoring();

      console.log('[Realtime] Recording started');
    } catch (error) {
      console.error('[Realtime] Failed to start recording:', error);
      throw error;
    }
  }

  /** Stop recording */
  stopRecording(): void {
    if (!this.isRecording) {
      return;
    }

    this.isRecording = false;

    // Stop volume monitoring
    if (this.chunkTimer) {
      cancelAnimationFrame(this.chunkTimer);
      this.chunkTimer = null;
    }

    // Flush remaining audio
    this.sendMessage({ type: 'flush' });

    // Cleanup audio resources
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor = null;
    }

    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    console.log('[Realtime] Recording stopped');
  }

  /** Check if currently recording */
  get recording(): boolean {
    return this.isRecording;
  }

  // ============================================================================
  // Public API - Configuration
  // ============================================================================

  /** Update configuration */
  setConfig(config: Partial<RealtimeConfig>): void {
    Object.assign(this.config, config);
    if (this.isConnected) {
      this.sendConfig();
    }
  }

  /** Set reference text for comparison */
  setReferenceText(text: string): void {
    this.config.referenceText = text;
    if (this.isConnected) {
      this.sendConfig();
    }
  }

  /** Set language */
  setLang(lang: string): void {
    this.config.lang = lang;
    if (this.isConnected) {
      this.sendConfig();
    }
  }

  /** Reset audio buffer on server */
  reset(): void {
    this.sendMessage({ type: 'reset' });
  }

  // ============================================================================
  // Private Methods
  // ============================================================================

  private sendMessage(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private sendConfig(): void {
    this.sendMessage({
      type: 'config',
      data: {
        lang: this.config.lang,
        reference_text: this.config.referenceText,
        mode: this.config.mode,
        evaluation_level: this.config.evaluationLevel,
      },
    });
  }

  private sendAudioChunk(pcmData: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(pcmData);
    }
  }

  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data) as Record<string, unknown>;
      const msgType = message.type as string;
      
      switch (msgType) {
        case 'state':
          const state = message as unknown as StreamState;
          this.onStateCallbacks.forEach(cb => cb(state));
          break;

        case 'transcription':
          const transcription = this.snakeToCamel(message) as unknown as TranscriptionResult;
          this.onTranscriptionCallbacks.forEach(cb => cb(transcription));
          break;

        case 'comparison':
          const comparison = this.snakeToCamel(message) as unknown as ComparisonResult;
          this.onComparisonCallbacks.forEach(cb => cb(comparison));
          break;

        case 'error':
          const error = message as unknown as RealtimeError;
          console.error('[Realtime] Server error:', error);
          this.onErrorCallbacks.forEach(cb => cb(error));
          break;

        case 'ready':
          console.log('[Realtime] Server ready:', message);
          break;

        case 'pong':
          // Keepalive response
          break;

        default:
          console.warn('[Realtime] Unknown message type:', message);
      }
    } catch (error) {
      console.error('[Realtime] Failed to parse message:', error);
    }
  }

  private floatTo16BitPCM(float32Array: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    
    return buffer;
  }

  private startVolumeMonitoring(): void {
    if (!this.analyser) return;

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    const updateVolume = () => {
      if (!this.isRecording || !this.analyser) return;

      this.analyser.getByteFrequencyData(dataArray);
      
      // Calculate RMS volume
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / dataArray.length);
      const volume = Math.min(1, rms / 128); // Normalize to 0-1

      this.onVolumeCallbacks.forEach(cb => cb(volume));

      this.chunkTimer = requestAnimationFrame(updateVolume);
    };

    updateVolume();
  }

  private snakeToCamel(obj: Record<string, unknown>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const key in obj) {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      result[camelKey] = obj[key];
    }
    return result;
  }

  private cleanup(): void {
    this.stopRecording();
    this.ws = null;
  }
}

// ============================================================================
// Factory function
// ============================================================================

export function createRealtimeClient(config?: RealtimeConfig): RealtimeClient {
  return new RealtimeClient(config);
}

export default RealtimeClient;
