/**
 * Compare Module - Renders pronunciation comparison results
 * 
 * Provides visual components for displaying:
 * - Score bar (0-100)
 * - Alignment table with color-coded operations
 * - Error summary
 */

import type { CompareResponse, EditOp } from './types/api';

/**
 * Render a score bar with gradient colors
 */
export function renderScoreBar(score: number): string {
    const percentage = Math.min(100, Math.max(0, score));
    const color = getScoreColor(percentage);

    return `
    <div class="score-container">
      <div class="score-label">Puntuación: <strong>${percentage.toFixed(0)}</strong>/100</div>
      <div class="score-bar-bg">
        <div class="score-bar-fill" style="width: ${percentage}%; background: ${color};"></div>
      </div>
    </div>
  `;
}

/**
 * Render alignment table showing ref vs hyp tokens
 */
export function renderAlignmentTable(ops: EditOp[]): string {
    if (!ops || ops.length === 0) {
        return '<p class="no-data">Sin datos de alineación</p>';
    }

    const rows = ops.map(op => {
        const refToken = op.ref ?? '—';
        const hypToken = op.hyp ?? '—';
        const opClass = getOpClass(op.op);
        const opLabel = getOpLabel(op.op);

        return `
      <tr class="op-row ${opClass}">
        <td class="token-ref">${escapeHtml(refToken)}</td>
        <td class="token-hyp">${escapeHtml(hypToken)}</td>
        <td class="op-type">${opLabel}</td>
      </tr>
    `;
    }).join('');

    return `
    <table class="alignment-table">
      <thead>
        <tr>
          <th>Referencia</th>
          <th>Tu pronunciación</th>
          <th>Resultado</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

/**
 * Render inline alignment (tokens side by side)
 */
export function renderInlineAlignment(ops: EditOp[]): string {
    if (!ops || ops.length === 0) {
        return '';
    }

    const tokens = ops.map(op => {
        const text = op.hyp ?? op.ref ?? '?';
        const opClass = getOpClass(op.op);
        return `<span class="token ${opClass}" title="${getOpLabel(op.op)}">${escapeHtml(text)}</span>`;
    }).join(' ');

    return `<div class="inline-alignment">${tokens}</div>`;
}

/**
 * Render error summary
 */
export function renderErrorSummary(response: CompareResponse): string {
    const { ops, per, score, mode, evaluation_level } = response;

    const counts = { eq: 0, sub: 0, ins: 0, del: 0 };
    for (const op of ops) {
        counts[op.op]++;
    }

    const total = ops.length;
    const errors = counts.sub + counts.ins + counts.del;

    return `
    <div class="error-summary">
      <div class="summary-row">
        <span class="label">Modo:</span>
        <span class="value">${mode}</span>
      </div>
      <div class="summary-row">
        <span class="label">Nivel:</span>
        <span class="value">${evaluation_level}</span>
      </div>
      <div class="summary-row">
        <span class="label">PER:</span>
        <span class="value">${(per * 100).toFixed(1)}%</span>
      </div>
      <div class="summary-row">
        <span class="label">Tokens:</span>
        <span class="value">${total} (${counts.eq} correctos, ${errors} errores)</span>
      </div>
      ${errors > 0 ? `
        <div class="error-breakdown">
          ${counts.sub > 0 ? `<span class="op-sub">Sustituciones: ${counts.sub}</span>` : ''}
          ${counts.ins > 0 ? `<span class="op-ins">Inserciones: ${counts.ins}</span>` : ''}
          ${counts.del > 0 ? `<span class="op-del">Omisiones: ${counts.del}</span>` : ''}
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * Render full comparison result
 */
export function renderCompareResult(response: CompareResponse): string {
    const score = response.score ?? (1 - response.per) * 100;

    return `
    <div class="compare-result">
      ${renderScoreBar(score)}
      ${renderErrorSummary(response)}
      <h4>Alineación de tokens</h4>
      ${renderInlineAlignment(response.ops)}
      <details>
        <summary>Ver tabla detallada</summary>
        ${renderAlignmentTable(response.ops)}
      </details>
    </div>
  `;
}

// === Helpers ===

function getScoreColor(score: number): string {
    if (score >= 80) return '#22c55e'; // green
    if (score >= 60) return '#eab308'; // yellow
    if (score >= 40) return '#f97316'; // orange
    return '#ef4444'; // red
}

function getOpClass(op: string): string {
    switch (op) {
        case 'eq': return 'op-eq';
        case 'sub': return 'op-sub';
        case 'ins': return 'op-ins';
        case 'del': return 'op-del';
        default: return '';
    }
}

function getOpLabel(op: string): string {
    switch (op) {
        case 'eq': return '✓ Correcto';
        case 'sub': return '✗ Sustitución';
        case 'ins': return '+ Inserción';
        case 'del': return '− Omisión';
        default: return op;
    }
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export default {
    renderScoreBar,
    renderAlignmentTable,
    renderInlineAlignment,
    renderErrorSummary,
    renderCompareResult,
};
