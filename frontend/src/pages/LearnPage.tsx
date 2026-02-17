import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Card, CardHeader, Spinner, Badge } from '@/components/common';
import { ReferenceInput, ChipGroup } from '@/components/practice';
import {
  RecordButton,
  Waveform,
  VolumeMeter,
  Countdown,
  QualityIndicator,
  TakeSelector,
} from '@/components/recording';
import { ScoreRing, InlineTokens } from '@/components/results';
import { FeedbackPanel } from '@/components/feedback';
import { useRecorder } from '@/hooks';
import api from '@/services/api';
import type {
  CompareResponse,
  FeedbackPayload,
  LearningOverview,
  SoundLesson,
  SupportedLang,
} from '@/types';

type LearningLevel = 'beginner' | 'intermediate' | 'advanced';

const LEARN_LANGUAGES: { value: SupportedLang; label: string }[] = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
];

const LEVELS: { value: LearningLevel; label: string }[] = [
  { value: 'beginner', label: 'Inicial' },
  { value: 'intermediate', label: 'Intermedio' },
  { value: 'advanced', label: 'Avanzado' },
];

const getDifficultyLabel = (difficulty?: number) => {
  if (!difficulty) return 'Nivel 1';
  if (difficulty <= 2) return 'Fácil';
  if (difficulty <= 3) return 'Medio';
  if (difficulty <= 4) return 'Difícil';
  return 'Muy difícil';
};

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    return (window as any).PRONUNCIAPA_API_BASE ?? document.body?.dataset?.apiBase ?? '';
  }
  return '';
};

const buildAudioUrl = (soundId: string, text: string) => {
  const encodedSound = encodeURIComponent(soundId);
  const encodedText = encodeURIComponent(text);
  return `${getApiBase()}/api/ipa-sounds/audio?sound_id=${encodedSound}&example=${encodedText}`;
};

const resolveAudioUrl = (url: string) => {
  if (url.startsWith('http') || url.startsWith('blob:')) return url;
  const base = getApiBase();
  if (!base) return url;
  return url.startsWith('/') ? `${base}${url}` : `${base}/${url}`;
};

export const LearnPage: React.FC = () => {
  const [lang, setLang] = useState<SupportedLang>('es');
  const [overview, setOverview] = useState<LearningOverview | null>(null);
  const [lesson, setLesson] = useState<SoundLesson | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<LearningLevel>('beginner');
  const [selectedSoundId, setSelectedSoundId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [loadingLesson, setLoadingLesson] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [referenceText, setReferenceText] = useState('');
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [feedbackResult, setFeedbackResult] = useState<FeedbackPayload | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const practiceRef = useRef<HTMLDivElement | null>(null);

  const { state: recState, countdown, currentUrl, takes, controls, getAnalyser } = useRecorder({
    maxDuration: 20,
    countdownSeconds: 3,
    maxTakes: 2,
  });

  const normalizedSounds = useMemo(() => {
    if (!overview) return [];
    return overview.sounds
      .map((sound) => {
        const id = sound.id;
        if (!id) return null;
        const ipa = sound.ipa ?? (id.includes('/') ? id.split('/').pop() : id);
        const name = sound.common_name ?? sound.label ?? sound.name ?? ipa ?? id;
        return {
          id,
          ipa,
          name,
          difficulty: sound.difficulty ?? 1,
        };
      })
      .filter(Boolean) as Array<{ id: string; ipa: string; name: string; difficulty: number }>;
  }, [overview]);

  const visibleSounds = useMemo(() => {
    if (!overview) return [];
    const progression = overview.progression?.[selectedLevel] ?? [];
    const progressionSounds = progression.filter((entry) => entry.includes('/'));
    let list = normalizedSounds;
    if (progressionSounds.length > 0) {
      list = normalizedSounds.filter((sound) => progressionSounds.includes(sound.id));
    }
    if (search.trim()) {
      const query = search.trim().toLowerCase();
      list = list.filter(
        (sound) =>
          sound.name.toLowerCase().includes(query) ||
          sound.ipa.toLowerCase().includes(query) ||
          sound.id.toLowerCase().includes(query),
      );
    }
    return list;
  }, [overview, selectedLevel, normalizedSounds, search]);

  const modules = overview?.modules ?? [];

  useEffect(() => {
    if (!selectedSoundId || !visibleSounds.length) return;
    if (!visibleSounds.find((sound) => sound.id === selectedSoundId)) {
      setSelectedSoundId(visibleSounds[0].id);
    }
  }, [visibleSounds, selectedSoundId]);
  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    setError(null);
    try {
      const data = await api.getLearningOverview(lang);
      setOverview(data);
      const progression = data.progression?.beginner ?? [];
      const firstSound = progression.find((entry) => entry.includes('/'));
      const fallback = data.sounds[0]?.id ?? null;
      setSelectedSoundId(firstSound ?? fallback);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el catálogo');
      setOverview(null);
      setSelectedSoundId(null);
    } finally {
      setLoadingOverview(false);
    }
  }, [lang]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const loadLesson = useCallback(async () => {
    if (!selectedSoundId) {
      setLesson(null);
      return;
    }
    setLoadingLesson(true);
    setError(null);
    setLesson(null);
    try {
      const soundKey = selectedSoundId.startsWith(`${lang}/`)
        ? selectedSoundId.slice(lang.length + 1)
        : selectedSoundId;
      const data = await api.getSoundLesson(lang, soundKey, {
        includeAudio: true,
        maxDrills: 12,
        generate: true,
      });
      setLesson(data);
      const initialTarget =
        data.drills?.find((d) => d.target)?.target ||
        data.drills?.find((d) => d.targets?.length)?.targets?.[0] ||
        data.drills?.find((d) => d.pairs?.length)?.pairs?.[0]?.[0] ||
        data.audio_examples?.[0]?.text ||
        '';
      setReferenceText(initialTarget ?? '');
      setCompareResult(null);
      setFeedbackResult(null);
      setPracticeError(null);
      setFeedbackError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar la lección');
    } finally {
      setLoadingLesson(false);
    }
  }, [lang, selectedSoundId]);

  useEffect(() => {
    loadLesson();
  }, [loadLesson]);

  const playAudio = useCallback((url: string) => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
    }
    audioRef.current.src = resolveAudioUrl(url);
    audioRef.current.play().catch(() => undefined);
  }, []);

  const handlePracticeTarget = useCallback((text: string) => {
    setReferenceText(text);
    setCompareResult(null);
    setFeedbackResult(null);
    setPracticeError(null);
    setFeedbackError(null);
    practiceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleRecord = useCallback(() => {
    if (recState.isRecording) {
      controls.stop();
    } else {
      setCompareResult(null);
      setFeedbackResult(null);
      setPracticeError(null);
      setFeedbackError(null);
      controls.start().catch((e) => {
        setPracticeError(e instanceof Error ? e.message : 'No se pudo acceder al micrófono');
      });
    }
  }, [recState.isRecording, controls]);

  const processAudio = useCallback(async (audioBlob: Blob) => {
    if (!referenceText.trim()) {
      setPracticeError('Selecciona un texto antes de grabar');
      return;
    }

    setIsProcessing(true);
    setPracticeError(null);
    setCompareResult(null);
    setFeedbackResult(null);
    setFeedbackError(null);

    try {
      const result = await api.compare({
        audio: audioBlob,
        text: referenceText,
        lang,
        mode: 'objective',
        evaluationLevel: 'phonemic',
      });
      setCompareResult(result);

      setIsFeedbackLoading(true);
      try {
        const fb = await api.feedback({
          audio: audioBlob,
          text: referenceText,
          lang,
          mode: 'objective',
          evaluationLevel: 'phonemic',
          feedbackLevel: 'casual',
        });
        setFeedbackResult(fb.feedback);
      } catch (err) {
        setFeedbackError(err instanceof Error ? err.message : 'Error al generar feedback');
      } finally {
        setIsFeedbackLoading(false);
      }
    } catch (err) {
      setPracticeError(err instanceof Error ? err.message : 'Error al procesar audio');
    } finally {
      setIsProcessing(false);
    }
  }, [referenceText, lang]);

  const handleSelectTake = useCallback((blob: Blob) => {
    processAudio(blob);
  }, [processAudio]);

  const handleSendCurrent = useCallback(() => {
    if (currentUrl) {
      fetch(currentUrl)
        .then((r) => r.blob())
        .then((blob) => processAudio(blob))
        .catch(() => setPracticeError('Error al procesar la grabación'));
    }
  }, [currentUrl, processAudio]);

  return (
    <div className="page-container">
      <div className="bg-animated" aria-hidden="true" />
      <Countdown value={countdown} />

      <div className="learn-grid">
        <div className="learn-panel">
          <Card>
            <CardHeader>Explorar</CardHeader>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label className="section-title" style={{ display: 'block' }} htmlFor="learn-lang">
                  Idioma
                </label>
                <select
                  id="learn-lang"
                  className="input-glass"
                  value={lang}
                  onChange={(e) => setLang(e.target.value as SupportedLang)}
                >
                  {LEARN_LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>

              <ChipGroup
                label="Nivel"
                options={LEVELS}
                value={selectedLevel}
                onChange={setSelectedLevel}
              />

              <div>
                <label className="section-title" style={{ display: 'block' }} htmlFor="learn-search">
                  Buscar sonido
                </label>
                <input
                  id="learn-search"
                  className="input-glass"
                  placeholder="Busca por IPA o nombre"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
          </Card>

          {modules.length > 0 && (
            <Card>
              <CardHeader>Fundamentos</CardHeader>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {modules.map((module) => (
                  <div
                    key={module.id}
                    style={{
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-glass)',
                      border: '1px solid var(--border-glass)',
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                      {module.title}
                    </div>
                    {module.description && (
                      <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                        {module.description}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <CardHeader>Sonidos</CardHeader>
            {loadingOverview && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Spinner />
                <span style={{ color: 'var(--text-secondary)' }}>Cargando catálogo...</span>
              </div>
            )}
            {!loadingOverview && (
              <div className="learn-sound-list">
                {visibleSounds.map((sound) => (
                  <button
                    key={sound.id}
                    type="button"
                    className={`learn-sound-item ${selectedSoundId === sound.id ? 'active' : ''}`}
                    onClick={() => setSelectedSoundId(sound.id)}
                  >
                    <div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-lg)' }}>
                        /{sound.ipa}/
                      </div>
                      <div style={{ fontSize: 'var(--text-sm)', opacity: 0.85 }}>
                        {sound.name}
                      </div>
                    </div>
                    <span style={{ fontSize: 'var(--text-xs)', opacity: 0.8 }}>
                      {getDifficultyLabel(sound.difficulty)}
                    </span>
                  </button>
                ))}
                {!visibleSounds.length && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                    Sin resultados para esta búsqueda.
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        <div className="learn-panel">
          {error && (
            <div className="quality-indicator" data-quality="bad">
              <span>✕</span>
              <span>{error}</span>
            </div>
          )}

          {loadingLesson && (
            <Card>
              <CardHeader>Lección</CardHeader>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Spinner />
                <span style={{ color: 'var(--text-secondary)' }}>Cargando lección...</span>
              </div>
            </Card>
          )}
          {lesson && (
            <Card>
              <CardHeader>Lección del sonido</CardHeader>
              <div className="learn-meta" style={{ marginBottom: '1rem' }}>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '3rem',
                    fontWeight: 600,
                  }}
                >
                  /{lesson.ipa}/
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>
                    {lesson.common_name || lesson.name || 'Sonido IPA'}
                  </div>
                  {lesson.name && (
                    <div style={{ color: 'var(--text-secondary)' }}>
                      {lesson.name}
                    </div>
                  )}
                </div>
                <Badge variant="info">{getDifficultyLabel(lesson.difficulty)}</Badge>
                {lesson.generated_drills && (
                  <Badge variant="warning">Drills generados</Badge>
                )}
              </div>

              {lesson.articulation?.description && (
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  {lesson.articulation.description}
                </p>
              )}

              {lesson.articulation && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '0.5rem',
                    marginBottom: '1rem',
                  }}
                >
                  {Object.entries(lesson.articulation)
                    .filter(([key, value]) => key !== 'description' && value)
                    .map(([key, value]) => (
                      <div
                        key={key}
                        style={{
                          padding: '0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--bg-glass)',
                          border: '1px solid var(--border-glass)',
                          fontSize: 'var(--text-sm)',
                        }}
                      >
                        <strong style={{ textTransform: 'capitalize' }}>{key}</strong>: {value}
                      </div>
                    ))}
                </div>
              )}

              {lesson.visual_guide && (
                <div style={{ marginBottom: '1rem' }}>
                  <div className="section-title">Guía visual</div>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '0.5rem',
                    }}
                  >
                    {Object.entries(lesson.visual_guide)
                      .filter(([, value]) => value)
                      .map(([key, value]) => (
                        <div
                          key={key}
                          style={{
                            padding: '0.75rem',
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--bg-glass)',
                            border: '1px solid var(--border-glass)',
                            fontSize: 'var(--text-sm)',
                          }}
                        >
                          <strong style={{ textTransform: 'capitalize' }}>{key}</strong>: {value}
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {lesson.audio_examples && lesson.audio_examples.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div className="section-title">Ejemplos</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {lesson.audio_examples.map((ex, idx) => (
                      <div
                        key={`${ex.text}-${idx}`}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.75rem',
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--bg-glass)',
                          border: '1px solid var(--border-glass)',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600 }}>{ex.text}</div>
                          {ex.ipa && (
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>
                              {ex.ipa}
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => ex.audio_url && playAudio(ex.audio_url)}
                            disabled={!ex.audio_url}
                          >
                            Escuchar
                          </button>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handlePracticeTarget(ex.text)}
                          >
                            Practicar
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {lesson.common_errors && lesson.common_errors.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div className="section-title">Errores comunes</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {lesson.common_errors.map((errItem, idx) => (
                      <div
                        key={`${errItem.example}-${idx}`}
                        style={{
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--color-warning-border)',
                          background: 'var(--color-warning-bg)',
                        }}
                      >
                        <div style={{ fontWeight: 600 }}>
                          {errItem.example || errItem.substitution}
                        </div>
                        {errItem.tip && (
                          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                            {errItem.tip}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {lesson.tips && lesson.tips.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div className="section-title">Tips</div>
                  <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                    {lesson.tips.map((tip, idx) => (
                      <li key={`${tip}-${idx}`} style={{ marginBottom: '0.25rem' }}>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {lesson.minimal_pairs && lesson.minimal_pairs.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div className="section-title">Pares mínimos</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {lesson.minimal_pairs.map((pair, idx) => {
                      const wordA = pair[1] ?? pair[0];
                      const wordB = pair[3] ?? pair[2];
                      return (
                        <div
                          key={`${wordA}-${wordB}-${idx}`}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '0.75rem',
                            padding: '0.75rem',
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--bg-glass)',
                            border: '1px solid var(--border-glass)',
                          }}
                        >
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600 }}>{wordA}</span>
                            <span style={{ color: 'var(--text-muted)' }}>vs</span>
                            <span style={{ fontWeight: 600 }}>{wordB}</span>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => playAudio(buildAudioUrl(lesson.sound_id, wordA))}
                            >
                              Escuchar A
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => playAudio(buildAudioUrl(lesson.sound_id, wordB))}
                            >
                              Escuchar B
                            </button>
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handlePracticeTarget(wordA)}
                            >
                              Practicar
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {lesson.drills && lesson.drills.length > 0 && (
                <div>
                  <div className="section-title">Ejercicios</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {lesson.drills.map((drill, idx) => {
                      const targets =
                        drill.targets_with_audio?.map((t) => ({
                          text: t.text,
                          audio: t.audio_url,
                        })) ??
                        drill.targets?.map((t) => ({ text: t })) ??
                        (drill.target ? [{ text: drill.target }] : []);
                      const pairs =
                        drill.pairs_with_audio?.map((p) => ({
                          word1: p.word1,
                          word2: p.word2,
                          audio1: p.audio1_url,
                          audio2: p.audio2_url,
                        })) ??
                        drill.pairs?.map((p) => ({ word1: p[0], word2: p[1] })) ??
                        [];

                      return (
                        <div
                          key={`${drill.type}-${idx}`}
                          style={{
                            padding: '0.75rem',
                            borderRadius: 'var(--radius-md)',
                            background: 'var(--bg-glass)',
                            border: '1px solid var(--border-glass)',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Badge variant="info">{drill.type}</Badge>
                            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                              {drill.instruction || 'Practica estos ejemplos'}
                            </span>
                          </div>

                          {drill.hints && drill.hints.length > 0 && (
                            <div style={{ marginTop: '0.5rem', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                              {drill.hints.join(' · ')}
                            </div>
                          )}

                          {targets.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                              {targets.map((target, tIdx) => (
                                <div
                                  key={`${target.text}-${tIdx}`}
                                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}
                                >
                                  <span style={{ fontWeight: 600 }}>{target.text}</span>
                                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => target.audio && playAudio(target.audio)}
                                      disabled={!target.audio}
                                    >
                                      Escuchar
                                    </button>
                                    <button
                                      className="btn btn-primary btn-sm"
                                      onClick={() => handlePracticeTarget(target.text)}
                                    >
                                      Practicar
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {pairs.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                              {pairs.map((pair, pIdx) => (
                                <div
                                  key={`${pair.word1}-${pair.word2}-${pIdx}`}
                                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}
                                >
                                  <span style={{ fontWeight: 600 }}>
                                    {pair.word1} <span style={{ color: 'var(--text-muted)' }}>vs</span> {pair.word2}
                                  </span>
                                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => pair.audio1 ? playAudio(pair.audio1) : playAudio(buildAudioUrl(lesson.sound_id, pair.word1))}
                                    >
                                      Escuchar A
                                    </button>
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => pair.audio2 ? playAudio(pair.audio2) : playAudio(buildAudioUrl(lesson.sound_id, pair.word2))}
                                    >
                                      Escuchar B
                                    </button>
                                    <button
                                      className="btn btn-primary btn-sm"
                                      onClick={() => handlePracticeTarget(pair.word1)}
                                    >
                                      Practicar
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </Card>
          )}
          <div ref={practiceRef}>
            <Card>
              <CardHeader>Practica inmediata</CardHeader>
              <ReferenceInput value={referenceText} onChange={setReferenceText} />

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                <Waveform
                  analyser={getAnalyser()}
                  active={recState.isRecording}
                  audioUrl={!recState.isRecording ? currentUrl : null}
                />

                {recState.isRecording && <VolumeMeter level={recState.audioLevel} />}

                <QualityIndicator
                  level={recState.quality.level}
                  message={recState.quality.message}
                  isClipping={recState.quality.isClipping}
                />

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <RecordButton
                    isRecording={recState.isRecording}
                    isProcessing={isProcessing}
                    onClick={handleRecord}
                    disabled={!referenceText.trim()}
                  />
                  {recState.isRecording && (
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--text-xl)',
                        fontWeight: 600,
                        color: 'var(--color-error)',
                      }}
                    >
                      {Math.floor(recState.duration / 60)}:
                      {Math.floor(recState.duration % 60)
                        .toString()
                        .padStart(2, '0')}
                    </span>
                  )}
                </div>

                {!recState.isRecording && currentUrl && (
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <audio src={currentUrl} controls style={{ flex: 1, height: 40 }} />
                    <button
                      className="btn btn-primary"
                      onClick={handleSendCurrent}
                      disabled={isProcessing}
                    >
                      {isProcessing ? <Spinner size={18} /> : 'Enviar'}
                    </button>
                    <button className="btn btn-secondary" onClick={() => controls.saveTake()}>
                      Guardar
                    </button>
                  </div>
                )}

                <TakeSelector
                  takes={takes}
                  currentUrl={null}
                  onSelect={handleSelectTake}
                  onRemove={controls.removeTake}
                  onSaveCurrent={controls.saveTake}
                  canSave={!!currentUrl}
                />

                {practiceError && (
                  <div className="quality-indicator" data-quality="bad">
                    <span>✕</span>
                    <span>{practiceError}</span>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {compareResult && (
            <Card className="fade-in">
              <CardHeader>Resultado</CardHeader>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                <ScoreRing score={compareResult.score ?? (1 - compareResult.per) * 100} />
                <InlineTokens ops={compareResult.ops} />
              </div>
            </Card>
          )}

          <FeedbackPanel feedback={feedbackResult} loading={isFeedbackLoading} error={feedbackError} />
        </div>
      </div>
    </div>
  );
};
