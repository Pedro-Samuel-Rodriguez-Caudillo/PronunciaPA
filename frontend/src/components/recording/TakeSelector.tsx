import React, { useRef } from 'react';
import type { Take } from '@/hooks/useRecorder';

interface TakeSelectorProps {
  takes: Take[];
  currentUrl: string | null;
  onSelect: (blob: Blob) => void;
  onRemove: (id: number) => void;
  onSaveCurrent: () => void;
  canSave: boolean;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export const TakeSelector: React.FC<TakeSelectorProps> = ({
  takes,
  currentUrl,
  onSelect,
  onRemove,
  onSaveCurrent,
  canSave,
}) => {
  const audioRefs = useRef<Record<number, HTMLAudioElement | null>>({});

  if (takes.length === 0 && !currentUrl) return null;

  return (
    <div className="glass-card" style={{ padding: '1rem' }}>
      <h4 className="section-title">Tomas grabadas</h4>

      {/* Current unsaved recording */}
      {currentUrl && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem',
            background: 'var(--bg-glass)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '0.75rem',
            border: '1px solid var(--border-focus)',
          }}
        >
          <span style={{ color: 'var(--color-info)', fontWeight: 600, fontSize: 'var(--text-sm)' }}>
            Nueva
          </span>
          <audio src={currentUrl} controls style={{ flex: 1, height: 32 }} />
          <button
            className="btn btn-primary btn-sm"
            onClick={onSaveCurrent}
            disabled={!canSave}
          >
            Guardar
          </button>
        </div>
      )}

      {/* Saved takes */}
      {takes.map((take, idx) => (
        <div
          key={take.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem',
            background: 'var(--bg-glass)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: idx < takes.length - 1 ? '0.5rem' : 0,
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: 'var(--text-sm)', minWidth: '2rem' }}>
            #{idx + 1}
          </span>
          <audio
            ref={(el) => { audioRefs.current[take.id] = el; }}
            src={take.url}
            controls
            style={{ flex: 1, height: 32 }}
          />
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
            {formatDuration(take.duration)}
          </span>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onSelect(take.blob)}
            aria-label={`Usar toma ${idx + 1}`}
          >
            Usar
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => onRemove(take.id)}
            aria-label={`Eliminar toma ${idx + 1}`}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
};
