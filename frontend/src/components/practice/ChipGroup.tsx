import React from 'react';

interface ChipOption<T extends string> {
  value: T;
  label: string;
  description?: string;
}

interface ChipGroupProps<T extends string> {
  label: string;
  options: ChipOption<T>[];
  value: T;
  onChange: (value: T) => void;
}

export function ChipGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: ChipGroupProps<T>) {
  const selected = options.find((o) => o.value === value);

  return (
    <div>
      <span className="section-title" style={{ display: 'block' }}>
        {label}
      </span>
      <div className="chip-group" role="radiogroup" aria-label={label}>
        {options.map((opt) => (
          <button
            key={opt.value}
            className="chip"
            role="radio"
            aria-checked={value === opt.value}
            aria-pressed={value === opt.value}
            onClick={() => onChange(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {selected?.description && (
        <p
          style={{
            marginTop: '0.35rem',
            fontSize: 'var(--text-xs, 0.75rem)',
            color: 'var(--text-muted)',
            lineHeight: 1.45,
          }}
        >
          {selected.description}
        </p>
      )}
    </div>
  );
}
