import React from 'react';
import type { FeedbackPayload } from '@/types';
import { Card, CardHeader, Spinner, Badge } from '@/components/common';

interface FeedbackPanelProps {
  feedback: FeedbackPayload | null;
  loading: boolean;
  error: string | null;
}

export const FeedbackPanel: React.FC<FeedbackPanelProps> = ({
  feedback,
  loading,
  error,
}) => {
  if (loading) {
    return (
      <Card>
        <CardHeader>Feedback</CardHeader>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem 0' }}>
          <Spinner />
          <span style={{ color: 'var(--text-secondary)' }}>Generando feedback...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>Feedback</CardHeader>
        <div className="quality-indicator" data-quality="bad">
          <span>⚠</span>
          <span>{error}</span>
        </div>
      </Card>
    );
  }

  if (!feedback) return null;

  return (
    <Card className="fade-in">
      <CardHeader>Feedback</CardHeader>

      {/* Summary */}
      <div style={{ marginBottom: '1rem' }}>
        <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)', lineHeight: 1.6 }}>
          {feedback.summary}
        </p>
      </div>

      {/* Short Advice */}
      {feedback.advice_short && (
        <div
          style={{
            padding: '1rem',
            background: 'var(--color-info-bg)',
            borderRadius: 'var(--radius-sm)',
            borderLeft: '3px solid var(--color-info)',
            marginBottom: '1rem',
          }}
        >
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
            💡 {feedback.advice_short}
          </p>
        </div>
      )}

      {/* Detailed Advice (collapsible) */}
      {feedback.advice_long && (
        <details style={{ marginBottom: '1rem' }}>
          <summary
            style={{
              cursor: 'pointer',
              color: 'var(--text-secondary)',
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              padding: '0.5rem 0',
            }}
          >
            Ver explicación detallada
          </summary>
          <div
            style={{
              padding: '1rem',
              background: 'var(--bg-glass)',
              borderRadius: 'var(--radius-sm)',
              marginTop: '0.5rem',
              fontSize: 'var(--text-sm)',
              color: 'var(--text-secondary)',
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
            }}
          >
            {feedback.advice_long}
          </div>
        </details>
      )}

      {/* Drills */}
      {feedback.drills && feedback.drills.length > 0 && (
        <div>
          <h4
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginBottom: '0.5rem',
            }}
          >
            Ejercicios recomendados
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {feedback.drills.map((drill, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  background: 'var(--bg-glass)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <Badge variant="info">{drill.type}</Badge>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>
                  {drill.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {feedback.warnings && feedback.warnings.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          {feedback.warnings.map((w, i) => (
            <div
              key={i}
              className="quality-indicator"
              data-quality="warning"
              style={{ marginBottom: '0.25rem' }}
            >
              <span>⚠</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};
