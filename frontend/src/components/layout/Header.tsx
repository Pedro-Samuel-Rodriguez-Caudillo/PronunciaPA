import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@/hooks';

interface HeaderProps {
  onNavigate?: (path: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ onNavigate }) => {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
      return;
    }
    navigate(path);
  };

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 'var(--z-sticky)' as any,
        background: 'var(--bg-glass)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-glass)',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault();
            handleNavigate('/');
          }}
          style={{
            fontSize: 'var(--text-xl)',
            fontWeight: 800,
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            textDecoration: 'none',
            cursor: 'pointer',
          }}
        >
          PronunciaPA
        </a>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
          beta
        </span>
      </div>

      <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <a
          href="/learn"
          onClick={(e) => {
            e.preventDefault();
            handleNavigate('/learn');
          }}
          className="btn btn-ghost btn-sm"
          style={{ textDecoration: 'none' }}
        >
          Aprender
        </a>
        <a
          href="/practice"
          onClick={(e) => {
            e.preventDefault();
            handleNavigate('/practice');
          }}
          className="btn btn-ghost btn-sm"
          style={{ textDecoration: 'none' }}
        >
          Practicar
        </a>
        <button
          className="btn btn-ghost btn-icon"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </nav>
    </header>
  );
};
