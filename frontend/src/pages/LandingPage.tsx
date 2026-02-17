import React from 'react';
import { useNavigate } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      <div className="bg-animated" aria-hidden="true" />

      {/* Hero */}
      <section
        style={{
          textAlign: 'center',
          padding: '6rem 0 4rem',
          maxWidth: 700,
          margin: '0 auto',
        }}
      >
        <h1
          style={{
            fontSize: 'var(--text-5xl)',
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: '1.5rem',
          }}
        >
          Mejora tu{' '}
          <span
            style={{
              background: 'var(--gradient-primary)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            pronunciación
          </span>{' '}
          con IA
        </h1>
        <p
          style={{
            fontSize: 'var(--text-lg)',
            color: 'var(--text-secondary)',
            marginBottom: '2rem',
            lineHeight: 1.7,
          }}
        >
          PronunciaPA analiza tu pronunciación fonema por fonema usando IPA,
          compara con la referencia y te da feedback personalizado con
          inteligencia artificial.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate('/practice')}
          >
            Empezar a practicar
          </button>
          <button
            className="btn btn-secondary btn-lg"
            onClick={() => navigate('/learn')}
          >
            Aprender sonidos
          </button>
          <a
            href="https://github.com/pronunciapa"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary btn-lg"
            style={{ textDecoration: 'none' }}
          >
            Ver en GitHub
          </a>
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: '4rem 0' }}>
        <h2
          className="section-title"
          style={{ textAlign: 'center', marginBottom: '2rem', fontSize: 'var(--text-sm)' }}
        >
          Características
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {FEATURES.map((f) => (
            <div key={f.title} className="glass-card slide-up">
              <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>{f.icon}</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: '0.5rem' }}>
                {f.title}
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.6 }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          textAlign: 'center',
          padding: '4rem 0',
        }}
      >
        <div
          className="glass-card"
          style={{
            maxWidth: 500,
            margin: '0 auto',
            textAlign: 'center',
          }}
        >
          <h2 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: '1rem' }}>
            ¿Listo para mejorar?
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Graba, analiza y aprende. Sin cuenta, sin instalación.
          </p>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate('/learn')}
          >
            Empezar lecciones
          </button>
        </div>
      </section>
    </div>
  );
};

const FEATURES = [
  {
    icon: '🎙️',
    title: 'Grabación Premium',
    desc: 'Visualización de onda en tiempo real, reducción de ruido, calibración de micrófono y múltiples tomas.',
  },
  {
    icon: '🔤',
    title: 'Análisis IPA',
    desc: 'Transcripción fonética precisa con Allosaurus, normalización multilenguaje y distancia articulatoria.',
  },
  {
    icon: '📊',
    title: 'Comparación Detallada',
    desc: 'Alineación token a token, detección de sustituciones, inserciones y omisiones con puntuación ponderada.',
  },
  {
    icon: '🤖',
    title: 'Feedback con IA',
    desc: 'Consejos personalizados generados por LLM con ejercicios recomendados y nivel de detalle ajustable.',
  },
  {
    icon: '🏆',
    title: 'Gamificación',
    desc: 'Sistema de XP, niveles, rachas diarias y logros para mantener la motivación.',
  },
  {
    icon: '🌐',
    title: 'Multilenguaje',
    desc: 'Soporte para español, inglés, francés y alemán con inventarios fonéticos específicos.',
  },
];
