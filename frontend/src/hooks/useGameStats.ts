import { useState, useCallback, useEffect } from 'react';

export interface GameStats {
  level: number;
  levelName: string;
  xp: number;
  xpToNext: number;
  streak: number;
  totalPractices: number;
  avgScore: number;
  achievements: string[];
  lastPracticeDate: string | null;
}

const STORAGE_KEY = 'pronunciapa-game-stats';
const USER_ID_KEY = 'pronunciapa-user-id';

const LEVELS = [
  { name: 'Principiante', xp: 0 },
  { name: 'Aprendiz', xp: 100 },
  { name: 'Intermedio', xp: 300 },
  { name: 'Avanzado', xp: 600 },
  { name: 'Experto', xp: 1000 },
  { name: 'Maestro', xp: 1500 },
  { name: 'Gran Maestro', xp: 2200 },
  { name: 'Legendario', xp: 3000 },
];

const ACHIEVEMENTS: Record<string, { name: string; desc: string; check: (s: GameStats) => boolean }> = {
  first_practice: { name: 'Primera Práctica', desc: 'Completa tu primera práctica', check: (s) => s.totalPractices >= 1 },
  ten_practices: { name: 'Dedicación', desc: 'Completa 10 prácticas', check: (s) => s.totalPractices >= 10 },
  streak_3: { name: 'En Racha', desc: 'Alcanza una racha de 3 días', check: (s) => s.streak >= 3 },
  streak_7: { name: 'Consistente', desc: 'Alcanza una racha de 7 días', check: (s) => s.streak >= 7 },
  perfect_score: { name: 'Perfección', desc: 'Obtén un puntaje de 100', check: () => false }, // checked manually
  high_avg: { name: 'Alto Nivel', desc: 'Promedio mayor a 80', check: (s) => s.avgScore > 80 && s.totalPractices >= 5 },
};

function defaultStats(): GameStats {
  return {
    level: 0,
    levelName: LEVELS[0].name,
    xp: 0,
    xpToNext: LEVELS[1].xp,
    streak: 0,
    totalPractices: 0,
    avgScore: 0,
    achievements: [],
    lastPracticeDate: null,
  };
}

function loadStats(): GameStats {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultStats();
    return { ...defaultStats(), ...JSON.parse(raw) };
  } catch {
    return defaultStats();
  }
}

function saveStats(stats: GameStats): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
}

function computeLevel(xp: number): { level: number; levelName: string; xpToNext: number } {
  let level = 0;
  for (let i = LEVELS.length - 1; i >= 0; i--) {
    if (xp >= LEVELS[i].xp) {
      level = i;
      break;
    }
  }
  const next = LEVELS[level + 1];
  return {
    level,
    levelName: LEVELS[level].name,
    xpToNext: next ? next.xp : LEVELS[LEVELS.length - 1].xp,
  };
}

export function ensureUserId(): string {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

export function useGameStats() {
  const [stats, setStats] = useState<GameStats>(loadStats);

  // Persist on every change
  useEffect(() => {
    saveStats(stats);
  }, [stats]);

  const addPractice = useCallback((score: number) => {
    setStats((prev) => {
      const today = new Date().toISOString().slice(0, 10);
      const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

      // Streak logic
      let newStreak = prev.streak;
      if (prev.lastPracticeDate === today) {
        // Same day, no streak change
      } else if (prev.lastPracticeDate === yesterday) {
        newStreak += 1;
      } else {
        newStreak = 1;
      }

      const totalPractices = prev.totalPractices + 1;
      const avgScore =
        (prev.avgScore * prev.totalPractices + score) / totalPractices;

      // XP: base 10 + score-based bonus
      const xpGain = 10 + Math.round(score / 10);
      const newXp = prev.xp + xpGain;
      const { level, levelName, xpToNext } = computeLevel(newXp);

      // Check achievements
      const newAchievements = [...prev.achievements];
      const candidate: GameStats = {
        ...prev,
        level,
        levelName,
        xp: newXp,
        xpToNext,
        streak: newStreak,
        totalPractices,
        avgScore,
        achievements: newAchievements,
        lastPracticeDate: today,
      };

      for (const [key, def] of Object.entries(ACHIEVEMENTS)) {
        if (!newAchievements.includes(key)) {
          if (key === 'perfect_score' && score >= 100) {
            newAchievements.push(key);
          } else if (def.check(candidate)) {
            newAchievements.push(key);
          }
        }
      }

      return {
        ...candidate,
        achievements: newAchievements,
      };
    });
  }, []);

  const getAchievementInfo = useCallback((key: string) => {
    return ACHIEVEMENTS[key] ?? { name: key, desc: '' };
  }, []);

  const resetStats = useCallback(() => {
    setStats(defaultStats());
  }, []);

  return {
    stats,
    addPractice,
    getAchievementInfo,
    resetStats,
    userId: ensureUserId(),
    levels: LEVELS,
  };
}
