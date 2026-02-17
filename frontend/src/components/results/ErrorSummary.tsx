import React from 'react';
import type { EditOp } from '@/types';

interface ErrorSummaryProps {
  ops: EditOp[];
}

export const ErrorSummary: React.FC<ErrorSummaryProps> = ({ ops }) => {
  const counts = { eq: 0, sub: 0, ins: 0, del: 0 };
  for (const op of ops) {
    counts[op.op] = (counts[op.op] || 0) + 1;
  }
  const total = ops.length;
  const errors = counts.sub + counts.ins + counts.del;

  if (total === 0) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
      <div className="badge badge-success">
        ✓ {counts.eq} correctos
      </div>
      {counts.sub > 0 && (
        <div className="badge badge-warning">
          ↔ {counts.sub} sustituciones
        </div>
      )}
      {counts.ins > 0 && (
        <div className="badge badge-info">
          + {counts.ins} inserciones
        </div>
      )}
      {counts.del > 0 && (
        <div className="badge badge-error">
          − {counts.del} omisiones
        </div>
      )}
      <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
        {total} tokens · {errors} errores · PER {total > 0 ? ((errors / total) * 100).toFixed(1) : 0}%
      </div>
    </div>
  );
};
