import { useState, useRef, useCallback, useEffect } from 'react';
import type { CompareResponse, TranscriptionResponse } from '@/types';

export type StreamStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'speaking'
  | 'processing'
  | 'error';

export interface RealtimeState {
  status: StreamStatus;
  volume: number;
  liveIpa: string;
  liveScore: number | null;
  lastTranscription: TranscriptionResponse | null;
  lastComparison: CompareResponse | null;
  error: string | null;
}

interface UseRealtimeOptions {
  wsUrl?: string;
  lang?: string;
  referenceText?: string;
  autoReconnect?: boolean;
}

interface WsMessage {
  type: string;
  data?: any;
  message?: string;
}

function floatTo16BitPCM(input: Float32Array): ArrayBuffer {
  const output = new ArrayBuffer(input.length * 2);
  const view = new DataView(output);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return output;
}

export function useRealtime(options: UseRealtimeOptions = {}) {
  const {
    wsUrl: customWsUrl,
    lang = 'es',
    referenceText = '',
    autoReconnect = false,
  } = options;

  const [state, setState] = useState<RealtimeState>({
    status: 'disconnected',
    volume: 0,
    liveIpa: '',
    liveScore: null,
    lastTranscription: null,
    lastComparison: null,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const getWsUrl = useCallback(() => {
    if (customWsUrl) return customWsUrl;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${proto}//${host}/ws/practice`;
  }, [customWsUrl]);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    processorRef.current?.disconnect();
    analyserRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    processorRef.current = null;
    analyserRef.current = null;
    streamRef.current = null;
    audioCtxRef.current = null;
  }, []);

  const monitorVolume = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);

    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    const avg = sum / data.length / 255;

    setState((prev) => ({ ...prev, volume: Math.min(1, avg * 3) }));
    rafRef.current = requestAnimationFrame(monitorVolume);
  }, []);

  const connect = useCallback(async () => {
    setState((prev) => ({ ...prev, status: 'connecting', error: null }));

    try {
      // Get mic
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      // Audio pipeline
      const audioCtx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Processor to capture PCM
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // WebSocket
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setState((prev) => ({ ...prev, status: 'connected' }));
        // Send config
        ws.send(
          JSON.stringify({
            type: 'config',
            data: { lang, reference_text: referenceText },
          }),
        );

        // Wire audio processing
        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const input = e.inputBuffer.getChannelData(0);
          const pcm = floatTo16BitPCM(input);
          ws.send(pcm);
        };

        source.connect(processor);
        processor.connect(audioCtx.destination);
        monitorVolume();

        setState((prev) => ({ ...prev, status: 'listening' }));
      };

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return;
        try {
          const msg: WsMessage = JSON.parse(event.data);
          switch (msg.type) {
            case 'state':
              setState((prev) => ({
                ...prev,
                status: msg.data?.status ?? prev.status,
              }));
              break;
            case 'transcription':
              setState((prev) => ({
                ...prev,
                liveIpa: msg.data?.ipa ?? '',
                lastTranscription: msg.data,
              }));
              break;
            case 'comparison':
              setState((prev) => ({
                ...prev,
                liveScore: msg.data?.score ?? null,
                lastComparison: msg.data,
              }));
              break;
            case 'error':
              setState((prev) => ({
                ...prev,
                error: msg.message ?? msg.data?.message ?? 'Error desconocido',
              }));
              break;
          }
        } catch {
          /* ignore parse errors */
        }
      };

      ws.onerror = () => {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: 'Error de conexión WebSocket',
        }));
      };

      ws.onclose = () => {
        cleanup();
        setState((prev) => ({ ...prev, status: 'disconnected', volume: 0 }));
        if (autoReconnect) {
          reconnectRef.current = setTimeout(() => connect(), 3000);
        }
      };
    } catch (err) {
      cleanup();
      setState((prev) => ({
        ...prev,
        status: 'error',
        error:
          err instanceof Error
            ? err.message
            : 'No se pudo acceder al micrófono',
      }));
    }
  }, [getWsUrl, lang, referenceText, autoReconnect, cleanup, monitorVolume]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectRef.current);
    cancelAnimationFrame(rafRef.current);

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    cleanup();

    setState({
      status: 'disconnected',
      volume: 0,
      liveIpa: '',
      liveScore: null,
      lastTranscription: null,
      lastComparison: null,
      error: null,
    });
  }, [cleanup]);

  const updateConfig = useCallback(
    (config: { lang?: string; referenceText?: string }) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(
        JSON.stringify({
          type: 'config',
          data: {
            lang: config.lang,
            reference_text: config.referenceText,
          },
        }),
      );
    },
    [],
  );

  const flush = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'flush' }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(reconnectRef.current);
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    state,
    connect,
    disconnect,
    updateConfig,
    flush,
    isConnected: state.status !== 'disconnected' && state.status !== 'error',
  };
}
