import React from 'react';
import type { GameStats } from '@/hooks/useGameStats';

interface StatsPanelProps {
  stats: GameStats;
  getAchievementInfo: (key: string) => { name: string; desc: string };
}

export const StatsPanel: React.FC<StatsPanelProps> = ({
  stats,
  getAchievementInfo,
}) => {
  const xpProgress = stats.xpToNext > 0
    ? Math.min(100, (stats.xp / stats.xpToNext) * 100)
    : 100;

  return (
    <div className="glass-card fade-in" style={{ padding: '1.25rem' }}>
      <h3 className="section-title">Progreso</h3>

      {/* Level & XP */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div>
          <span style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>{stats.levelName}</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: 'var(--text-sm)' }}>
            Nivel {stats.level + 1}
          </span>
        </div>
        <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', fontWeight: 600 }}>
          {stats.xp} / {stats.xpToNext} XP
        </span>
      </div>

      {/* XP Bar */}
      <div style={{ width: '100%', height: 8, background: 'var(--bg-glass)', borderRadius: 'var(--radius-full)', overflow: 'hidden', marginBottom: '1rem' }}>
        <div
          style={{
            height: '100%',
            width: `${xpProgress}%`,
            background: 'var(--gradient-primary)',
            borderRadius: 'var(--radius-full)',
            transition: 'width 0.5s ease',
          }}
        />
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700 }}>{stats.totalPractices}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Prácticas</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700 }}>
            {stats.avgScore > 0 ? Math.round(stats.avgScore) : '—'}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Promedio</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700 }}>🔥 {stats.streak}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Racha</div>
        </div>
      </div>

      {/* Achievements */}
      {stats.achievements.length > 0 && (
        <div>
          <h4 style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.5rem' }}>
            Logros
          </h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {stats.achievements.map((key) => {
              const info = getAchievementInfo(key);
              return (
                <span
                  key={key}
                  className="badge badge-success"
                  title={info.desc}
                >
                  🏆 {info.name}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
