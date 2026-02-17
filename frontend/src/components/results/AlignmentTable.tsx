import React from 'react';
import type { EditOp } from '@/types';

interface AlignmentTableProps {
  ops: EditOp[];
  alignment: Array<[string | null, string | null]>;
}

function opLabel(op: string): string {
  switch (op) {
    case 'eq': return 'Correcto';
    case 'sub': return 'Sustitución';
    case 'ins': return 'Inserción';
    case 'del': return 'Omisión';
    default: return op;
  }
}

export const AlignmentTable: React.FC<AlignmentTableProps> = ({ ops, alignment }) => {
  if (!ops.length && !alignment.length) return null;

  // Prefer alignment pairs if available
  const items = alignment.length > 0
    ? alignment.map(([ref, hyp], i) => ({
        ref,
        hyp,
        op: ops[i]?.op ?? (ref === hyp ? 'eq' : ref && hyp ? 'sub' : ref ? 'del' : 'ins'),
      }))
    : ops.map((o) => ({ ref: o.ref ?? null, hyp: o.hyp ?? null, op: o.op }));

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
            <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600 }}>
              Referencia
            </th>
            <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600 }}>
              Observado
            </th>
            <th style={{ padding: '0.5rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600 }}>
              Resultado
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border-glass)' }}>
              <td style={{ padding: '0.5rem' }}>
                {item.ref ? (
                  <span className={`phoneme-token ${item.op === 'del' ? 'delete' : item.op === 'eq' ? 'correct' : 'substitute'}`}>
                    {item.ref}
                  </span>
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>—</span>
                )}
              </td>
              <td style={{ padding: '0.5rem' }}>
                {item.hyp ? (
                  <span className={`phoneme-token ${item.op === 'ins' ? 'insert' : item.op === 'eq' ? 'correct' : 'substitute'}`}>
                    {item.hyp}
                  </span>
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>—</span>
                )}
              </td>
              <td style={{ padding: '0.5rem' }}>
                <span className={`badge badge-${item.op === 'eq' ? 'success' : item.op === 'sub' ? 'warning' : 'error'}`}>
                  {opLabel(item.op)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
