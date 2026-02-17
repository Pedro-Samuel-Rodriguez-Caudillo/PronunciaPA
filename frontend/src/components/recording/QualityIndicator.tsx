import React from 'react';

interface QualityIndicatorProps {
  level: 'good' | 'warning' | 'bad' | 'idle';
  message: string;
  isClipping?: boolean;
}

export const QualityIndicator: React.FC<QualityIndicatorProps> = ({
  level,
  message,
  isClipping,
}) => {
  if (level === 'idle' || !message) return null;

  const icons: Record<string, string> = {
    good: '✓',
    warning: '⚠',
    bad: '✕',
  };

  return (
    <div
      className="quality-indicator fade-in"
      data-quality={level}
      role="status"
      aria-live="polite"
    >
      <span aria-hidden="true">{icons[level]}</span>
      <span>{message}</span>
      {isClipping && (
        <span className="badge badge-error" style={{ marginLeft: '0.5rem' }}>
          CLIP
        </span>
      )}
    </div>
  );
};
