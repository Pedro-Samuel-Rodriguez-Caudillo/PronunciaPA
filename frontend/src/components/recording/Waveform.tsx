import React, { useRef, useEffect, useCallback } from 'react';

interface WaveformProps {
  /** The AnalyserNode to read audio data from */
  analyser: AnalyserNode | null;
  /** Whether recording is active */
  active: boolean;
  /** Canvas height in pixels */
  height?: number;
  /** CSS class for the container */
  className?: string;
  /** Optional recorded blob to show static waveform */
  audioUrl?: string | null;
}

export const Waveform: React.FC<WaveformProps> = ({
  analyser,
  active,
  height = 80,
  className = '',
  audioUrl,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const staticDataRef = useRef<Float32Array | null>(null);

  // Draw live waveform from AnalyserNode
  const drawLive = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const h = canvas.height;
    const bufferLength = analyser.fftSize;
    const dataArray = new Float32Array(bufferLength);
    analyser.getFloatTimeDomainData(dataArray);

    ctx.clearRect(0, 0, width, h);

    // Gradient stroke
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, '#667eea');
    gradient.addColorStop(1, '#764ba2');

    ctx.lineWidth = 2;
    ctx.strokeStyle = gradient;
    ctx.beginPath();

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i];
      const y = (v * 0.5 + 0.5) * h;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      x += sliceWidth;
    }

    ctx.stroke();

    // Glow effect
    ctx.shadowColor = '#667eea';
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0;

    if (active) {
      rafRef.current = requestAnimationFrame(drawLive);
    }
  }, [analyser, active]);

  // Draw static waveform from decoded audio buffer
  const drawStatic = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas || !audioUrl) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    try {
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioCtx = new AudioContext();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
      const rawData = audioBuffer.getChannelData(0);
      audioCtx.close();

      // Downsample to canvas width
      const width = canvas.width;
      const h = canvas.height;
      const samples = Math.floor(rawData.length / width);
      const filtered = new Float32Array(width);

      for (let i = 0; i < width; i++) {
        let sum = 0;
        for (let j = 0; j < samples; j++) {
          sum += Math.abs(rawData[i * samples + j]);
        }
        filtered[i] = sum / samples;
      }

      staticDataRef.current = filtered;

      // Normalize
      const max = Math.max(...filtered, 0.01);

      ctx.clearRect(0, 0, width, h);

      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      gradient.addColorStop(0, '#667eea');
      gradient.addColorStop(1, '#764ba2');

      ctx.fillStyle = gradient;
      const mid = h / 2;

      for (let i = 0; i < width; i++) {
        const amplitude = (filtered[i] / max) * mid * 0.9;
        ctx.fillRect(i, mid - amplitude, 1, amplitude * 2);
      }
    } catch {
      // Failed to decode — show flat line
      const width = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, width, h);
      ctx.strokeStyle = 'var(--text-muted)';
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(width, h / 2);
      ctx.stroke();
    }
  }, [audioUrl]);

  // Resize canvas to match container
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        canvas.width = entry.contentRect.width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      }
    });

    resizeObserver.observe(canvas);
    return () => resizeObserver.disconnect();
  }, [height]);

  // Start/stop live drawing
  useEffect(() => {
    if (active && analyser) {
      drawLive();
    } else {
      cancelAnimationFrame(rafRef.current);
    }
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, analyser, drawLive]);

  // Draw static waveform when audioUrl changes
  useEffect(() => {
    if (!active && audioUrl) {
      drawStatic();
    }
  }, [active, audioUrl, drawStatic]);

  return (
    <canvas
      ref={canvasRef}
      className={`waveform-canvas ${className}`}
      style={{ width: '100%', height }}
      role="img"
      aria-label={active ? 'Audio en vivo' : 'Forma de onda de la grabación'}
    />
  );
};
