import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, Spinner } from '@/components/common';
import api from '@/services/api';
import type { LessonPlanResponse, RoadmapProgressResponse, RoadmapTopicProgress } from '@/types';

const DEFAULT_LANG = 'es';
const DEFAULT_USER = 'demo';

const LEVEL_COLORS: Record<string, string> = {
  not_started: 'var(--text-muted)',
  in_progress: 'var(--color-warning, #f59e0b)',
  proficient: 'var(--color-info, #3b82f6)',
  completed: 'var(--color-success, #22c55e)',
};

const LEVEL_LABELS: Record<string, string> = {
  not_started: 'Sin iniciar',
  in_progress: 'En progreso',
  proficient: 'Avanzado',
  completed: 'Completado',
};

const LEVEL_PROGRESS: Record<string, number> = {
  not_started: 0,
  in_progress: 35,
  proficient: 70,
  completed: 100,
};

interface TopicCardProps {
  topic: RoadmapTopicProgress;
  isFocus: boolean;
  onStudy: (topicId: string) => void;
}

const TopicCard: React.FC<TopicCardProps> = ({ topic, isFocus, onStudy }) => {
  const color = LEVEL_COLORS[topic.level] ?? 'var(--text-muted)';
  const progress = LEVEL_PROGRESS[topic.level] ?? 0;

  return (
    <div
      style={{
        border: isFocus
          ? `2px solid ${LEVEL_COLORS.in_progress}`
          : '1px solid var(--border-glass)',
        borderRadius: '0.75rem',
        padding: '1rem 1.25rem',
        background: isFocus ? 'var(--bg-card-hover, rgba(245,158,11,0.06))' : 'var(--bg-card)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        position: 'relative',
      }}
    >
      {isFocus && (
        <span
          style={{
            position: 'absolute',
            top: '0.5rem',
            right: '0.75rem',
            fontSize: '0.65rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: LEVEL_COLORS.in_progress,
            background: 'rgba(245,158,11,0.12)',
            borderRadius: '0.25rem',
            padding: '0.1rem 0.4rem',
          }}
        >
          Siguiente
        </span>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{topic.name}</span>
        <span style={{ fontSize: '0.75rem', color, fontWeight: 500 }}>
          {LEVEL_LABELS[topic.level] ?? topic.level}
        </span>
      </div>
      {/* Progress bar */}
      <div
        style={{
          height: '4px',
          background: 'var(--bg-surface, rgba(255,255,255,0.08))',
          borderRadius: '2px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progress}%`,
            background: color,
            borderRadius: '2px',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      {topic.level !== 'completed' && (
        <button
          onClick={() => onStudy(topic.topic_id)}
          style={{
            marginTop: '0.25rem',
            padding: '0.35rem 0.75rem',
            border: `1px solid ${color}`,
            borderRadius: '0.5rem',
            background: 'transparent',
            color,
            fontSize: '0.8rem',
            fontWeight: 500,
            cursor: 'pointer',
            alignSelf: 'flex-start',
          }}
        >
          Practicar
        </button>
      )}
    </div>
  );
};

export const ProgressPage: React.FC = () => {
  const navigate = useNavigate();
  const [lang] = useState(DEFAULT_LANG);
  const [userId] = useState(DEFAULT_USER);

  const [roadmap, setRoadmap] = useState<RoadmapProgressResponse | null>(null);
  const [lessonPlan, setLessonPlan] = useState<LessonPlanResponse | null>(null);
  const [loadingRoadmap, setLoadingRoadmap] = useState(false);
  const [loadingLesson, setLoadingLesson] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load roadmap progress
  useEffect(() => {
    setLoadingRoadmap(true);
    api
      .getRoadmapProgress(userId, lang)
      .then(setRoadmap)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingRoadmap(false));
  }, [userId, lang]);

  // Load personalised lesson plan
  useEffect(() => {
    setLoadingLesson(true);
    api
      .getLessonPlan(userId, lang)
      .then(setLessonPlan)
      .catch(() => setLessonPlan(null)) // non-fatal — LLM might not be configured
      .finally(() => setLoadingLesson(false));
  }, [userId, lang]);

  const handleStudyTopic = (topicId: string) => {
    // Navigate to LearnPage; it will show the IPA catalog where users can practice
    navigate(`/learn?topic=${encodeURIComponent(topicId)}&lang=${lang}`);
  };

  const handleStartNextLesson = () => {
    if (!lessonPlan) return;
    navigate(
      `/learn?sound=${encodeURIComponent(lessonPlan.recommended_sound_id)}&lang=${lang}`,
    );
  };

  // Determine which topic is "next"
  const nextTopicId =
    lessonPlan?.topic_id ??
    roadmap?.topics.find((t) => t.level === 'in_progress')?.topic_id ??
    roadmap?.topics.find((t) => t.level === 'not_started')?.topic_id;

  return (
    <div
      style={{
        maxWidth: '800px',
        margin: '0 auto',
        padding: '2rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '2rem',
      }}
    >
      {/* Title */}
      <div>
        <h1
          style={{
            fontSize: 'var(--text-2xl)',
            fontWeight: 800,
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            margin: 0,
          }}
        >
          Tu progreso
        </h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.4rem', fontSize: '0.9rem' }}>
          Roadmap de pronunciación en español · Usuario: <strong>{userId}</strong>
        </p>
      </div>

      {/* Next lesson recommendation */}
      {(loadingLesson || lessonPlan) && (
        <Card>
          <CardHeader>📖 Próxima lección recomendada</CardHeader>
          {loadingLesson ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 0' }}>
              <Spinner size={16} />
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Generando lección personalizada…
              </span>
            </div>
          ) : lessonPlan ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <p style={{ margin: 0, lineHeight: 1.6 }}>{lessonPlan.intro}</p>
              {lessonPlan.tips.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {lessonPlan.tips.map((tip, i) => (
                    <li key={i} style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                      {tip}
                    </li>
                  ))}
                </ul>
              )}
              {lessonPlan.drills.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {lessonPlan.drills.map((drill, i) => (
                    <div
                      key={i}
                      style={{
                        background: 'var(--bg-surface)',
                        borderRadius: '0.5rem',
                        padding: '0.35rem 0.7rem',
                        fontSize: '0.82rem',
                        fontFamily: 'monospace',
                        border: '1px solid var(--border-glass)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', marginRight: '0.3rem' }}>
                        [{drill.type}]
                      </span>
                      {drill.text}
                    </div>
                  ))}
                </div>
              )}
              <div>
                <button
                  onClick={handleStartNextLesson}
                  style={{
                    padding: '0.6rem 1.25rem',
                    borderRadius: '0.6rem',
                    border: 'none',
                    background: 'var(--gradient-primary)',
                    color: '#fff',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                  }}
                >
                  Empezar lección → /{lessonPlan.recommended_sound_id}/
                </button>
              </div>
            </div>
          ) : null}
        </Card>
      )}

      {/* Roadmap */}
      <Card>
        <CardHeader>🗺️ Roadmap de pronunciación</CardHeader>
        {error ? (
          <p style={{ color: 'var(--color-error, #ef4444)', fontSize: '0.85rem' }}>
            {error}
          </p>
        ) : loadingRoadmap ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 0' }}>
            <Spinner size={16} />
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Cargando progreso…</span>
          </div>
        ) : !roadmap || roadmap.topics.length === 0 ? (
          <div style={{ padding: '1rem 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            <p>Aún no tienes progreso registrado.</p>
            <p>
              Practica con el micrófono en{' '}
              <button
                onClick={() => navigate('/learn')}
                style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', textDecoration: 'underline', fontSize: 'inherit' }}
              >
                Aprende
              </button>{' '}
              o{' '}
              <button
                onClick={() => navigate('/practice')}
                style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', textDecoration: 'underline', fontSize: 'inherit' }}
              >
                Practica
              </button>{' '}
              para ver tu roadmap.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            {roadmap.topics.map((topic) => (
              <TopicCard
                key={topic.topic_id}
                topic={topic}
                isFocus={topic.topic_id === nextTopicId}
                onStudy={handleStudyTopic}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
