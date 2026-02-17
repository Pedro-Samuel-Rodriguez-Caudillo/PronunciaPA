import React from 'react';

interface VolumeMeterProps {
  level: number; // 0-1
  className?: string;
}

function getVolumeLabel(level: number): string {
  if (level > 0.9) return 'clip';
  if (level > 0.7) return 'hot';
  if (level > 0.15) return 'good';
  return 'low';
}

export const VolumeMeter: React.FC<VolumeMeterProps> = ({ level, className = '' }) => {
  const label = getVolumeLabel(level);
  const pct = Math.round(level * 100);

  return (
    <div className={`volume-meter ${className}`} role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Nivel de volumen">
      <div
        className="volume-meter-fill"
        data-level={label}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
};
