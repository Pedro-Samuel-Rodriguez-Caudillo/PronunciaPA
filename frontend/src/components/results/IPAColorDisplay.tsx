/**
 * IPAColorDisplay — visualización dual de tokens IPA con colores semánticos.
 *
 * Muestra cada fonema con:
 *   verde   → correcto (eq)
 *   amarillo → sustitución cercana (distancia articulatoria < 0.3)
 *   rojo     → error (sub lejana, ins, del)
 *   gris     → token OOV (fuera del inventario del pack)
 *
 * Toggle técnico (IPA puro) ↔ casual (transliteración coloquial).
 * Soporta nivel fonémico y fonético de forma transparente.
 */
import { useState, useCallback } from 'react';
import type { IPADisplay, IPADisplayToken, DisplayMode, TokenColor } from '../../types/api';

// ---------------------------------------------------------------------------
// Constantes de estilo
// ---------------------------------------------------------------------------

const COLOR_CLASSES: Record<TokenColor, { bg: string; text: string; border: string }> = {
  green:  { bg: 'bg-green-100',  text: 'text-green-700',  border: 'border-green-300' },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' },
  red:    { bg: 'bg-red-100',    text: 'text-red-700',    border: 'border-red-300' },
  gray:   { bg: 'bg-gray-100',   text: 'text-gray-500',   border: 'border-gray-300' },
};

const SCORE_COLOR_CLASSES: Record<TokenColor, string> = {
  green:  'text-green-600',
  yellow: 'text-yellow-600',
  red:    'text-red-600',
  gray:   'text-gray-500',
};

// ---------------------------------------------------------------------------
// Tipos de props
// ---------------------------------------------------------------------------

interface IPAColorDisplayProps {
  /** Datos de visualización del backend. */
  display: IPADisplay;
  /** Modo de inicio. Por defecto usa el del backend. */
  initialMode?: DisplayMode;
  /** Mostrar leyenda de colores. Por defecto true. */
  showLegend?: boolean;
  /** Mostrar distancia articulatoria en tooltip. Por defecto false. */
  showArticulatoryDistance?: boolean;
  /** Callback cuando el usuario cambia de modo. */
  onModeChange?: (mode: DisplayMode) => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Sub-componente: token individual
// ---------------------------------------------------------------------------

interface TokenChipProps {
  token: IPADisplayToken;
  mode: DisplayMode;
  showDistance: boolean;
}

function TokenChip({ token, mode, showDistance }: TokenChipProps) {
  const displayText = mode === 'casual' ? token.casual : token.ipa;
  const refText = token.ref && token.ref !== token.ipa
    ? (mode === 'casual' ? token.casual : token.ref)
    : null;

  const cls = COLOR_CLASSES[token.color] ?? COLOR_CLASSES.gray;
  const title = showDistance && token.articulatory_distance != null
    ? `Distancia articulatoria: ${token.articulatory_distance.toFixed(2)}`
    : token.op === 'sub'
      ? `${token.ref ?? '—'} → ${token.hyp ?? '—'}`
      : undefined;

  return (
    <span
      title={title}
      className={`
        inline-flex flex-col items-center
        px-2.5 py-1.5 rounded-lg border
        font-mono text-base font-semibold
        select-none cursor-default
        ${cls.bg} ${cls.text} ${cls.border}
      `}
    >
      {displayText || '∅'}
      {refText && token.op === 'sub' && (
        <span className="text-[10px] text-gray-400 line-through leading-none mt-0.5">
          {refText}
        </span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Sub-componente: toggle técnico / casual
// ---------------------------------------------------------------------------

interface ModeToggleProps {
  mode: DisplayMode;
  onToggle: () => void;
}

function ModeToggle({ mode, onToggle }: ModeToggleProps) {
  return (
    <button
      onClick={onToggle}
      className="flex items-center gap-0.5 rounded-full bg-gray-100 p-0.5 text-xs font-medium"
      title="Alternar modo técnico (IPA) ↔ casual"
      aria-label={`Cambiar a modo ${mode === 'technical' ? 'casual' : 'técnico'}`}
    >
      <span
        className={`
          flex items-center gap-1 rounded-full px-3 py-1 transition-all
          ${mode === 'technical' ? 'bg-indigo-600 text-white' : 'text-gray-500'}
        `}
      >
        <span>IPA</span>
      </span>
      <span
        className={`
          flex items-center gap-1 rounded-full px-3 py-1 transition-all
          ${mode === 'casual' ? 'bg-indigo-600 text-white' : 'text-gray-500'}
        `}
      >
        <span>ABC</span>
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Sub-componente: leyenda
// ---------------------------------------------------------------------------

function Legend({ legend }: { legend: Record<string, string> }) {
  const entries: Array<[TokenColor, string]> = [
    ['green',  legend['green']  ?? 'Correcto'],
    ['yellow', legend['yellow'] ?? 'Cercano'],
    ['red',    legend['red']    ?? 'Error'],
    ['gray',   legend['gray']   ?? 'Fuera de inventario'],
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
      {entries.map(([color, label]) => {
        const cls = COLOR_CLASSES[color];
        return (
          <span key={color} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span className={`w-2.5 h-2.5 rounded-full ${cls.bg} border ${cls.border}`} />
            {label}
          </span>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function IPAColorDisplay({
  display,
  initialMode,
  showLegend = true,
  showArticulatoryDistance = false,
  onModeChange,
  className = '',
}: IPAColorDisplayProps) {
  const [mode, setMode] = useState<DisplayMode>(initialMode ?? display.mode);

  const handleToggle = useCallback(() => {
    const next: DisplayMode = mode === 'technical' ? 'casual' : 'technical';
    setMode(next);
    onModeChange?.(next);
  }, [mode, onModeChange]);

  const refText = mode === 'casual' ? display.ref_casual : display.ref_technical;
  const hypText = mode === 'casual' ? display.hyp_casual : display.hyp_technical;

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {display.level === 'phonetic' ? 'Fonético' : 'Fonémico'}
          </span>
        </div>
        <ModeToggle mode={mode} onToggle={handleToggle} />
      </div>

      {/* Referencia (objetivo) */}
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
          Objetivo
        </p>
        <p className="font-mono text-base text-slate-600 leading-relaxed">
          {refText || '—'}
        </p>
      </div>

      {/* Tokens coloreados */}
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
          Tu pronunciación
        </p>
        <div className="flex flex-wrap gap-1.5">
          {display.tokens.length > 0
            ? display.tokens.map((token, i) => (
                <TokenChip
                  key={i}
                  token={token}
                  mode={mode}
                  showDistance={showArticulatoryDistance}
                />
              ))
            : <span className="text-gray-400 text-sm">—</span>
          }
        </div>
        {hypText && (
          <p className="font-mono text-xs text-slate-400 mt-1.5">
            {hypText}
          </p>
        )}
      </div>

      {/* Leyenda */}
      {showLegend && <Legend legend={display.legend} />}
    </div>
  );
}

export default IPAColorDisplay;
