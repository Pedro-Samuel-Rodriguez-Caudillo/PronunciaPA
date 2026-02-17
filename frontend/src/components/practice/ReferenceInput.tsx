import React from 'react';

interface ReferenceInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export const ReferenceInput: React.FC<ReferenceInputProps> = ({
  value,
  onChange,
  placeholder = 'Escribe la frase que vas a pronunciar...',
}) => {
  return (
    <div>
      <label
        htmlFor="reference-text"
        className="section-title"
        style={{ display: 'block' }}
      >
        Texto de referencia
      </label>
      <textarea
        id="reference-text"
        className="input-glass"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={2}
        style={{ resize: 'vertical', minHeight: 60 }}
        aria-label="Texto de referencia para practicar"
      />
    </div>
  );
};
