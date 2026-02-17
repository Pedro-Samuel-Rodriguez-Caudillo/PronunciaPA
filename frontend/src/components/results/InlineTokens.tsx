import React from 'react';
import type { EditOp } from '@/types';

interface InlineTokensProps {
  ops: EditOp[];
}

export const InlineTokens: React.FC<InlineTokensProps> = ({ ops }) => {
  if (!ops.length) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.15rem' }} role="list" aria-label="Tokens IPA">
      {ops.map((op, i) => {
        const display = op.op === 'del' ? op.ref : op.hyp ?? op.ref ?? '';
        return (
          <span
            key={i}
            className={`phoneme-token`}
            data-op={op.op}
            role="listitem"
            title={
              op.op === 'sub'
                ? `${op.ref} → ${op.hyp}`
                : op.op === 'ins'
                  ? `Insertado: ${op.hyp}`
                  : op.op === 'del'
                    ? `Omitido: ${op.ref}`
                    : `Correcto: ${op.ref}`
            }
          >
            {display}
          </span>
        );
      })}
    </div>
  );
};
