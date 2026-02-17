import { useState, useRef, useCallback, useEffect } from 'react';

export interface RecorderState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioLevel: number;
  /** Real-time quality assessment */
  quality: AudioQuality;
}

export interface AudioQuality {
  level: 'good' | 'warning' | 'bad' | 'idle';
  message: string;
  isClipping: boolean;
  noiseFloor: number;
}

export interface RecorderControls {
  start: () => Promise<void>;
  stop: () => void;
  reset: () => void;
}

export interface RecorderResult {
  blob: Blob | null;
  url: string | null;
  takes: Take[];
}

export interface Take {
  id: number;
  blob: Blob;
  url: string;
  duration: number;
}

interface UseRecorderOptions {
  /** Max recording duration in seconds */
  maxDuration?: number;
  /** Enable countdown before recording */
  countdownSeconds?: number;
  /** Max number of takes to keep */
  maxTakes?: number;
  /** Audio constraints overrides */
  audioConstraints?: MediaTrackConstraints;
}

const DEFAULT_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  sampleRate: 16000,
};

function getSupportedMimeType(): string {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/wav',
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return 'audio/webm';
}

export function useRecorder(options: UseRecorderOptions = {}) {
  const {
    maxDuration = 30,
    countdownSeconds = 3,
    maxTakes = 3,
    audioConstraints,
  } = options;

  const [state, setState] = useState<RecorderState>({
    isRecording: false,
    isPaused: false,
    duration: 0,
    audioLevel: 0,
    quality: { level: 'idle', message: '', isClipping: false, noiseFloor: 0 },
  });

  const [countdown, setCountdown] = useState<number | null>(null);
  const [currentBlob, setCurrentBlob] = useState<Blob | null>(null);
  const [currentUrl, setCurrentUrl] = useState<string | null>(null);
  const [takes, setTakes] = useState<Take[]>([]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number>(0);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const noiseFloorRef = useRef<number>(0);
  const takeIdRef = useRef<number>(0);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAnimationFrame(rafRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close();
      takes.forEach((t) => URL.revokeObjectURL(t.url));
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const monitorAudio = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const dataArray = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(dataArray);

    let sum = 0;
    let peak = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const abs = Math.abs(dataArray[i]);
      sum += abs * abs;
      if (abs > peak) peak = abs;
    }
    const rms = Math.sqrt(sum / dataArray.length);
    const level = Math.min(1, rms * 5); // Scale for UI
    const isClipping = peak > 0.95;

    // Update noise floor (rolling min of RMS when level is low)
    if (rms < 0.02) {
      noiseFloorRef.current = Math.max(noiseFloorRef.current, rms);
    }

    let qualityLevel: AudioQuality['level'] = 'good';
    let message = '';
    if (isClipping) {
      qualityLevel = 'bad';
      message = 'Aléjate del micrófono — se detecta clipping';
    } else if (rms < 0.005) {
      qualityLevel = 'warning';
      message = 'No se detecta audio — habla más fuerte';
    } else if (rms < 0.01) {
      qualityLevel = 'warning';
      message = 'Volumen bajo — acércate al micrófono';
    }

    setState((prev) => ({
      ...prev,
      audioLevel: level,
      quality: {
        level: qualityLevel,
        message,
        isClipping,
        noiseFloor: noiseFloorRef.current,
      },
    }));

    rafRef.current = requestAnimationFrame(monitorAudio);
  }, []);

  const startRecording = useCallback(async () => {
    // Run countdown first
    if (countdownSeconds > 0) {
      for (let i = countdownSeconds; i > 0; i--) {
        setCountdown(i);
        await new Promise((r) => setTimeout(r, 1000));
      }
      setCountdown(null);
    }

    const constraints: MediaStreamConstraints = {
      audio: { ...DEFAULT_CONSTRAINTS, ...audioConstraints },
    };

    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    streamRef.current = stream;

    // Set up audio analysis
    const audioCtx = new AudioContext();
    audioContextRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);

    // Highpass filter to remove rumble (80Hz)
    const highpass = audioCtx.createBiquadFilter();
    highpass.type = 'highpass';
    highpass.frequency.value = 80;
    source.connect(highpass);

    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.3;
    highpass.connect(analyser);
    analyserRef.current = analyser;

    // Start MediaRecorder
    const mimeType = getSupportedMimeType();
    const recorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const url = URL.createObjectURL(blob);

      // Revoke previous URL
      if (currentUrl) URL.revokeObjectURL(currentUrl);

      setCurrentBlob(blob);
      setCurrentUrl(url);
    };

    recorder.start(100); // Collect data every 100ms
    startTimeRef.current = Date.now();

    // Duration timer
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      setState((prev) => ({ ...prev, duration: elapsed }));

      if (elapsed >= maxDuration) {
        stopRecording();
      }
    }, 100);

    // Start audio monitoring
    noiseFloorRef.current = 0;
    monitorAudio();

    setState((prev) => ({
      ...prev,
      isRecording: true,
      duration: 0,
      quality: { level: 'good', message: '', isClipping: false, noiseFloor: 0 },
    }));
  }, [countdownSeconds, audioConstraints, maxDuration, monitorAudio, currentUrl]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }

    // Stop all tracks
    streamRef.current?.getTracks().forEach((t) => t.stop());

    // Stop monitoring
    cancelAnimationFrame(rafRef.current);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Close audio context
    audioContextRef.current?.close();
    audioContextRef.current = null;
    analyserRef.current = null;

    setState((prev) => ({
      ...prev,
      isRecording: false,
      audioLevel: 0,
      quality: { level: 'idle', message: '', isClipping: false, noiseFloor: 0 },
    }));
  }, []);

  const saveTake = useCallback(() => {
    if (!currentBlob || !currentUrl) return;

    takeIdRef.current += 1;
    const newTake: Take = {
      id: takeIdRef.current,
      blob: currentBlob,
      url: currentUrl,
      duration: state.duration,
    };

    setTakes((prev) => {
      const updated = [...prev, newTake];
      // Remove oldest if exceeding maxTakes
      while (updated.length > maxTakes) {
        const removed = updated.shift()!;
        URL.revokeObjectURL(removed.url);
      }
      return updated;
    });

    setCurrentBlob(null);
    setCurrentUrl(null);
  }, [currentBlob, currentUrl, state.duration, maxTakes]);

  const reset = useCallback(() => {
    stopRecording();
    takes.forEach((t) => URL.revokeObjectURL(t.url));
    if (currentUrl) URL.revokeObjectURL(currentUrl);
    setTakes([]);
    setCurrentBlob(null);
    setCurrentUrl(null);
    setState({
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioLevel: 0,
      quality: { level: 'idle', message: '', isClipping: false, noiseFloor: 0 },
    });
  }, [stopRecording, takes, currentUrl]);

  const removeTake = useCallback((id: number) => {
    setTakes((prev) => {
      const take = prev.find((t) => t.id === id);
      if (take) URL.revokeObjectURL(take.url);
      return prev.filter((t) => t.id !== id);
    });
  }, []);

  const getAnalyser = useCallback((): AnalyserNode | null => {
    return analyserRef.current;
  }, []);

  return {
    state,
    countdown,
    currentBlob,
    currentUrl,
    takes,
    controls: {
      start: startRecording,
      stop: stopRecording,
      reset,
      saveTake,
      removeTake,
    },
    getAnalyser,
  };
}
