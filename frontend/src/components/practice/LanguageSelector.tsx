import React from 'react';
import type { SupportedLang } from '@/types';

interface LanguageSelectorProps {
  value: SupportedLang;
  onChange: (lang: SupportedLang) => void;
}

const LANGUAGES: { value: SupportedLang; label: string; flag: string }[] = [
  { value: 'es', label: 'Español', flag: '🇪🇸' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'fr', label: 'Français', flag: '🇫🇷' },
  { value: 'de', label: 'Deutsch', flag: '🇩🇪' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  value,
  onChange,
}) => {
  return (
    <div>
      <label
        htmlFor="lang-select"
        className="section-title"
        style={{ display: 'block' }}
      >
        Idioma
      </label>
      <select
        id="lang-select"
        value={value}
        onChange={(e) => onChange(e.target.value as SupportedLang)}
        className="input-glass"
        style={{ cursor: 'pointer' }}
        aria-label="Seleccionar idioma"
      >
        {LANGUAGES.map((l) => (
          <option key={l.value} value={l.value}>
            {l.flag} {l.label}
          </option>
        ))}
      </select>
    </div>
  );
};
