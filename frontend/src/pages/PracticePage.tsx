import React, { useState, useCallback } from 'react';
import { Card, CardHeader, Spinner } from '@/components/common';
import { LanguageSelector, ChipGroup, ReferenceInput, StatsPanel } from '@/components/practice';
import {
  RecordButton,
  Waveform,
  VolumeMeter,
  Countdown,
  QualityIndicator,
  TakeSelector,
} from '@/components/recording';
import { ScoreRing, AlignmentTable, InlineTokens, ErrorSummary } from '@/components/results';
import { FeedbackPanel } from '@/components/feedback';
import { useRecorder, useGameStats } from '@/hooks';
import api from '@/services/api';
import type {
  CompareResponse,
  FeedbackPayload,
  SupportedLang,
  CompareMode,
  TranscriptionMode,
  FeedbackLevel,
} from '@/types';

const COMPARE_MODES: { value: CompareMode; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'casual', label: 'Casual' },
  { value: 'objective', label: 'Objetivo' },
  { value: 'phonetic', label: 'Fonético' },
];

const TRANSCRIPTION_MODES: { value: TranscriptionMode; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'phonemic', label: 'Fonémico' },
  { value: 'phonetic', label: 'Fonético' },
];

const FEEDBACK_LEVELS: { value: FeedbackLevel; label: string }[] = [
  { value: 'casual', label: 'Amigable' },
  { value: 'precise', label: 'Técnico' },
];

export const PracticePage: React.FC = () => {
  // Settings state
  const [lang, setLang] = useState<SupportedLang>('es');
  const [compareMode, setCompareMode] = useState<CompareMode>('objective');
  const [transcriptionMode, setTranscriptionMode] = useState<TranscriptionMode>('auto');
  const [feedbackLevel, setFeedbackLevel] = useState<FeedbackLevel>('casual');
  const [referenceText, setReferenceText] = useState('');

  // Results state
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [feedbackResult, setFeedbackResult] = useState<FeedbackPayload | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  // Hooks
  const { state: recState, countdown, currentUrl, takes, controls, getAnalyser } = useRecorder({
    maxDuration: 30,
    countdownSeconds: 3,
    maxTakes: 3,
  });
  const { stats, addPractice, getAchievementInfo, userId } = useGameStats();

  const handleRecord = useCallback(() => {
    if (recState.isRecording) {
      controls.stop();
    } else {
      setCompareResult(null);
      setFeedbackResult(null);
      setError(null);
      setFeedbackError(null);
      controls.start().catch((e) => {
        setError(e instanceof Error ? e.message : 'No se pudo acceder al micrófono');
      });
    }
  }, [recState.isRecording, controls]);

  const processAudio = useCallback(async (audioBlob: Blob) => {
    if (!referenceText.trim()) {
      setError('Escribe un texto de referencia antes de enviar');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setCompareResult(null);
    setFeedbackResult(null);
    setFeedbackError(null);

    try {
      // Compare
      const result = await api.compare({
        audio: audioBlob,
        text: referenceText,
        lang,
        mode: compareMode === 'auto' ? undefined : compareMode,
        evaluationLevel: transcriptionMode === 'auto' ? undefined : transcriptionMode,
        userId,
      });
      setCompareResult(result);

      // Add practice to stats
      if (result.score != null) {
        addPractice(result.score);
      }

      // Request feedback
      setIsFeedbackLoading(true);
      try {
        const fb = await api.feedback({
          audio: audioBlob,
          text: referenceText,
          lang,
          mode: compareMode === 'auto' ? undefined : compareMode,
          evaluationLevel: transcriptionMode === 'auto' ? undefined : transcriptionMode,
          feedbackLevel,
          userId,
        });
        setFeedbackResult(fb.feedback);
      } catch (e) {
        setFeedbackError(e instanceof Error ? e.message : 'Error al generar feedback');
      } finally {
        setIsFeedbackLoading(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al procesar audio');
    } finally {
      setIsProcessing(false);
    }
  }, [referenceText, lang, compareMode, transcriptionMode, feedbackLevel, userId, addPractice]);

  const handleSelectTake = useCallback((blob: Blob) => {
    processAudio(blob);
  }, [processAudio]);

  const handleSendCurrent = useCallback(() => {
    if (currentUrl) {
      // Fetch the blob from URL
      fetch(currentUrl)
        .then((r) => r.blob())
        .then((blob) => processAudio(blob))
        .catch(() => setError('Error al procesar la grabación'));
    }
  }, [currentUrl, processAudio]);

  return (
    <div className="page-container">
      <Countdown value={countdown} />

      <div className="practice-grid">
        {/* Left Column: Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Settings Card */}
          <Card>
            <CardHeader>Configuración</CardHeader>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <LanguageSelector value={lang} onChange={setLang} />
              <ChipGroup
                label="Modo de comparación"
                options={COMPARE_MODES}
                value={compareMode}
                onChange={setCompareMode}
              />
              <ChipGroup
                label="Nivel de transcripción"
                options={TRANSCRIPTION_MODES}
                value={transcriptionMode}
                onChange={setTranscriptionMode}
              />
              <ChipGroup
                label="Nivel de feedback"
                options={FEEDBACK_LEVELS}
                value={feedbackLevel}
                onChange={setFeedbackLevel}
              />
            </div>
          </Card>

          {/* Reference Text */}
          <Card>
            <ReferenceInput value={referenceText} onChange={setReferenceText} />
          </Card>

          {/* Recording Section */}
          <Card>
            <CardHeader>Grabación</CardHeader>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
              {/* Waveform */}
              <Waveform
                analyser={getAnalyser()}
                active={recState.isRecording}
                audioUrl={!recState.isRecording ? currentUrl : null}
              />

              {/* Volume meter */}
              {recState.isRecording && (
                <VolumeMeter level={recState.audioLevel} />
              )}

              {/* Quality indicator */}
              <QualityIndicator
                level={recState.quality.level}
                message={recState.quality.message}
                isClipping={recState.quality.isClipping}
              />

              {/* Record button + timer */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
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
                      fontSize: 'var(--text-2xl)',
                      fontWeight: 600,
                      color: 'var(--color-error)',
                    }}
                    aria-live="polite"
                  >
                    {Math.floor(recState.duration / 60)}:
                    {Math.floor(recState.duration % 60)
                      .toString()
                      .padStart(2, '0')}
                  </span>
                )}
              </div>

              {!referenceText.trim() && !recState.isRecording && (
                <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center' }}>
                  Escribe un texto de referencia para poder grabar
                </p>
              )}

              {/* Playback & Send */}
              {!recState.isRecording && currentUrl && (
                <div style={{ display: 'flex', gap: '0.75rem', width: '100%' }}>
                  <audio src={currentUrl} controls style={{ flex: 1, height: 40 }} />
                  <button
                    className="btn btn-primary"
                    onClick={handleSendCurrent}
                    disabled={isProcessing}
                  >
                    {isProcessing ? <Spinner size={18} /> : 'Enviar'}
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => controls.saveTake()}
                  >
                    Guardar toma
                  </button>
                </div>
              )}
            </div>

            {/* Takes */}
            <TakeSelector
              takes={takes}
              currentUrl={null}
              onSelect={handleSelectTake}
              onRemove={controls.removeTake}
              onSaveCurrent={controls.saveTake}
              canSave={!!currentUrl}
            />
          </Card>

          {/* Error */}
          {error && (
            <div
              className="quality-indicator fade-in"
              data-quality="bad"
              role="alert"
            >
              <span>✕</span>
              <span>{error}</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setError(null)}
                style={{ marginLeft: 'auto' }}
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Score */}
          {compareResult && (
            <Card className="fade-in">
              <CardHeader>Resultado</CardHeader>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                <ScoreRing score={compareResult.score ?? (1 - compareResult.per) * 100} />
                <div style={{ textAlign: 'center' }}>
                  <span className="badge badge-info" style={{ marginRight: '0.5rem' }}>
                    {compareResult.mode}
                  </span>
                  <span className="badge badge-info">
                    {compareResult.evaluation_level}
                  </span>
                </div>
              </div>
            </Card>
          )}

          {/* IPA Tokens */}
          {compareResult && (
            <Card className="fade-in">
              <CardHeader>Alineación IPA</CardHeader>
              <InlineTokens ops={compareResult.ops} />
              <div style={{ marginTop: '1rem' }}>
                <ErrorSummary ops={compareResult.ops} />
              </div>
            </Card>
          )}

          {/* Alignment Table */}
          {compareResult && (
            <Card className="fade-in">
              <CardHeader>Detalle de alineación</CardHeader>
              <AlignmentTable
                ops={compareResult.ops}
                alignment={compareResult.alignment}
              />
            </Card>
          )}

          {/* Feedback */}
          <FeedbackPanel
            feedback={feedbackResult}
            loading={isFeedbackLoading}
            error={feedbackError}
          />

          {/* Stats */}
          <StatsPanel stats={stats} getAchievementInfo={getAchievementInfo} />
        </div>
      </div>
    </div>
  );
};
