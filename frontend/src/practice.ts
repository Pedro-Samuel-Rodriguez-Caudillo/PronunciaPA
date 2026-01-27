/**
 * PronunciaPA Practice Page
 * Interactive pronunciation practice with recording, real-time feedback, and gamification
 */

import { createApiClient, type CompareRequest } from './api';
import type { CompareResponse, FeedbackResponse } from './types/api';
import type { IpaCliPayload, IpaExample } from './types/ipa';

// ============================================================================
// Types
// ============================================================================

type TranscriptionMode = 'phonemic' | 'phonetic';
type FeedbackLevel = 'casual' | 'precise';
type CompareMode = 'casual' | 'objective' | 'phonetic';

interface GameStats {
    level: number;
    xp: number;
    xpToNextLevel: number;
    streak: number;
    totalPractices: number;
    avgScore: number;
    achievements: string[];
}

interface SessionState {
    lang: string;
    mode: TranscriptionMode;
    feedbackLevel: FeedbackLevel;
    compareMode: CompareMode;
    referenceText: string;
    isRecording: boolean;
    isProcessing: boolean;
    isFeedbackLoading: boolean;
    recordingSeconds: number;
    lastResult: CompareResponse | null;
    lastFeedback: FeedbackResponse | null;
    feedbackError: string | null;
    ipaPayload: IpaCliPayload | null;
    ipaError: string | null;
    error: string | null;
}

// ============================================================================
// Constants
// ============================================================================

const LEVEL_NAMES: Record<number, string> = {
    1: 'Principiante',
    2: 'Aprendiz',
    3: 'Intermedio',
    4: 'Avanzado',
    5: 'Experto',
    6: 'Maestro',
    7: 'Virtuoso',
    8: 'Legendario',
};

const COLORS = {
    primary: '#667eea',
    primaryDark: '#5567d8',
    secondary: '#764ba2',
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
};

const DEFAULT_COMPARE_MODE: CompareMode = 'objective';

// ============================================================================
// State
// ============================================================================

let state: SessionState = {
    lang: 'es',
    mode: 'phonemic',
    feedbackLevel: 'casual',
    compareMode: DEFAULT_COMPARE_MODE,
    referenceText: '',
    isRecording: false,
    isProcessing: false,
    isFeedbackLoading: false,
    recordingSeconds: 0,
    lastResult: null,
    lastFeedback: null,
    feedbackError: null,
    ipaPayload: null,
    ipaError: null,
    error: null,
};

let stats: GameStats = loadStats();

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let recordingTimer: number | null = null;

const api = createApiClient();

// ============================================================================
// Storage
// ============================================================================

function loadStats(): GameStats {
    try {
        const stored = localStorage.getItem('pronunciapa_stats');
        if (stored) {
            return JSON.parse(stored);
        }
    } catch (e) {
        console.warn('Failed to load stats', e);
    }
    return {
        level: 1,
        xp: 0,
        xpToNextLevel: 100,
        streak: 0,
        totalPractices: 0,
        avgScore: 0,
        achievements: [],
    };
}

function saveStats(): void {
    try {
        localStorage.setItem('pronunciapa_stats', JSON.stringify(stats));
    } catch (e) {
        console.warn('Failed to save stats', e);
    }
}

function savePreferences(): void {
    try {
        localStorage.setItem('pronunciapa_prefs', JSON.stringify({
            lang: state.lang,
            mode: state.mode,
            feedbackLevel: state.feedbackLevel,
            compareMode: state.compareMode,
        }));
    } catch (e) {
        console.warn('Failed to save preferences', e);
    }
}

function loadPreferences(): void {
    try {
        const stored = localStorage.getItem('pronunciapa_prefs');
        if (stored) {
            const prefs = JSON.parse(stored);
            state.lang = prefs.lang || 'es';
            state.mode = prefs.mode || 'phonemic';
            state.feedbackLevel = prefs.feedbackLevel || 'casual';
            state.compareMode = prefs.compareMode || DEFAULT_COMPARE_MODE;
        }
    } catch (e) {
        console.warn('Failed to load preferences', e);
    }
}

// ============================================================================
// Gamification
// ============================================================================

function addPractice(score: number): string[] {
    const newAchievements: string[] = [];

    stats.totalPractices += 1;

    // Update average
    if (stats.avgScore === 0) {
        stats.avgScore = score;
    } else {
        stats.avgScore = (stats.avgScore * (stats.totalPractices - 1) + score) / stats.totalPractices;
    }

    // XP based on score
    const xpEarned = Math.floor(score * 100);
    stats.xp += xpEarned;

    // Level up
    while (stats.xp >= stats.xpToNextLevel) {
        stats.xp -= stats.xpToNextLevel;
        stats.level += 1;
        stats.xpToNextLevel = Math.floor(stats.xpToNextLevel * 1.5);
        newAchievements.push(`🎉 ¡Nivel ${stats.level} alcanzado!`);
    }

    // Achievements
    if (stats.totalPractices === 1 && !stats.achievements.includes('first_practice')) {
        stats.achievements.push('first_practice');
        newAchievements.push('🏆 ¡Primera práctica completada!');
    } else if (stats.totalPractices === 10 && !stats.achievements.includes('ten_practices')) {
        stats.achievements.push('ten_practices');
        newAchievements.push('🏆 ¡10 prácticas! Estás en racha');
    } else if (stats.totalPractices === 100 && !stats.achievements.includes('hundred_practices')) {
        stats.achievements.push('hundred_practices');
        newAchievements.push('🏆 ¡100 prácticas! Eres un experto');
    }

    if (score >= 0.95 && !stats.achievements.includes('perfect_score')) {
        stats.achievements.push('perfect_score');
        newAchievements.push('⭐ ¡Pronunciación perfecta!');
    } else if (score >= 0.90 && !stats.achievements.includes('excellent_score')) {
        stats.achievements.push('excellent_score');
        newAchievements.push('⭐ ¡Excelente pronunciación!');
    }

    saveStats();
    return newAchievements;
}

// ============================================================================
// Recording
// ============================================================================

async function startRecording(): Promise<void> {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.start(100); // Collect data every 100ms
        state.isRecording = true;
        state.recordingSeconds = 0;
        state.error = null;

        // Timer for recording duration
        const startTime = Date.now();
        recordingTimer = window.setInterval(() => {
            state.recordingSeconds = (Date.now() - startTime) / 1000;
            renderRecordingState();
        }, 100);

        render();
    } catch (err) {
        state.error = 'No se pudo acceder al micrófono. Verifica los permisos.';
        render();
    }
}

async function stopRecording(): Promise<Blob> {
    return new Promise((resolve) => {
        if (!mediaRecorder) {
            resolve(new Blob());
            return;
        }

        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });

            // Stop all tracks
            mediaRecorder?.stream.getTracks().forEach(track => track.stop());

            if (recordingTimer) {
                clearInterval(recordingTimer);
                recordingTimer = null;
            }

            resolve(blob);
        };

        mediaRecorder.stop();
        state.isRecording = false;
    });
}

async function processRecording(): Promise<void> {
    const audioBlob = await stopRecording();

    if (audioBlob.size === 0) {
        state.error = 'No se grabó audio';
        render();
        return;
    }

    state.isProcessing = true;
    state.isFeedbackLoading = false;
    state.error = null;
    state.feedbackError = null;
    state.lastFeedback = null;
    render();

    try {
        const result = await api.compare({
            audio: audioBlob,
            text: state.referenceText,
            lang: state.lang,
            mode: state.compareMode,
            evaluationLevel: state.mode,
        });

        state.lastResult = result;
        state.isProcessing = false;

        // Calculate score and update gamification
        const score = 1 - (result.per || 0);
        const achievements = addPractice(score);

        // Show achievements
        if (achievements.length > 0) {
            showAchievements(achievements);
        }

        render();
    } catch (err) {
        state.isProcessing = false;
        state.error = err instanceof Error ? err.message : 'Error procesando audio';
        render();
        return;
    }

    state.isFeedbackLoading = true;
    render();
    try {
        const feedback = await api.feedback({
            audio: audioBlob,
            text: state.referenceText,
            lang: state.lang,
            mode: state.compareMode,
            evaluationLevel: state.mode,
            feedbackLevel: state.feedbackLevel,
        });
        state.lastFeedback = feedback;
    } catch (err) {
        state.feedbackError = err instanceof Error ? err.message : 'No se pudo generar feedback';
    } finally {
        state.isFeedbackLoading = false;
        render();
    }
}

// ============================================================================
// UI Helpers
// ============================================================================

function showAchievements(achievements: string[]): void {
    const container = document.createElement('div');
    container.className = 'achievements-popup';
    container.innerHTML = achievements.map(a => `<div class="achievement">${a}</div>`).join('');
    document.body.appendChild(container);

    setTimeout(() => {
        container.classList.add('fade-out');
        setTimeout(() => container.remove(), 500);
    }, 3000);
}

function getScoreColor(score: number): string {
    if (score >= 0.9) return COLORS.success;
    if (score >= 0.7) return COLORS.warning;
    return COLORS.error;
}

function getOpColor(op: string): string {
    switch (op) {
        case 'eq': return COLORS.success;
        case 'sub': return COLORS.warning;
        case 'del': return COLORS.error;
        case 'ins': return COLORS.info;
        default: return '#ffffff';
    }
}

function getLevelName(level: number): string {
    return LEVEL_NAMES[level] || `Nivel ${level}`;
}

function formatDrillLabel(drill: any): string {
    if (!drill) return '-';
    const type = drill.type ? `${drill.type}: ` : '';
    if (drill.text) return `${type}${drill.text}`;
    if (Array.isArray(drill.pair)) return `${type}${drill.pair.join(' vs ')}`;
    if (drill.sound) return `${type}${drill.sound}`;
    return type.trim() || 'drill';
}

function buildFeedbackNotice(report: any, feedback: any): string {
    const warnings = new Set<string>();
    const addWarnings = (value: any) => {
        if (Array.isArray(value)) {
            value.forEach((item) => {
                if (typeof item === 'string' && item.trim()) warnings.add(item.trim());
            });
        }
    };
    addWarnings(feedback?.warnings);
    addWarnings(report?.warnings);
    addWarnings(report?.meta?.warnings);
    const confidence =
        feedback?.confidence || report?.confidence || report?.meta?.confidence || '';
    if (!warnings.size && !confidence) return '';
    const confidenceLabels: Record<string, string> = {
        low: 'baja',
        normal: 'normal',
        high: 'alta',
    };
    const parts: string[] = [];
    if (confidence) {
        parts.push(`Confiabilidad: ${confidenceLabels[confidence] || confidence}`);
    }
    if (warnings.size) {
        parts.push(Array.from(warnings).join(' '));
    }
    return parts.join(' - ');
}

function parseIpaCliPayload(raw: any): IpaCliPayload | null {
    if (!raw || typeof raw !== 'object') return null;
    const kind = raw.kind as IpaCliPayload['kind'];
    if (!kind) return null;
    if (kind === 'ipa.practice.set' && Array.isArray(raw.items)) return raw;
    if (kind === 'ipa.explore' && Array.isArray(raw.examples)) return raw;
    if (kind === 'ipa.practice.result') return raw;
    if (kind === 'ipa.list-sounds') return raw;
    return null;
}

function getIpaExamples(payload: IpaCliPayload | null): IpaExample[] {
    if (!payload) return [];
    if (payload.kind === 'ipa.practice.set') return payload.items || [];
    if (payload.kind === 'ipa.explore') return payload.examples || [];
    if (payload.kind === 'ipa.practice.result' && payload.item) return [payload.item];
    return [];
}

function getIpaSummary(payload: IpaCliPayload | null): string {
    if (!payload) return 'Sin set cargado.';
    const count = getIpaExamples(payload).length;
    const sound = (payload as any).sound?.ipa || '';
    const kindLabel = payload.kind === 'ipa.explore' ? 'explore' : payload.kind.replace('ipa.', '');
    return `${sound ? `Sonido ${sound} · ` : ''}${kindLabel} · ${count} ejemplos`;
}

function loadIpaPayloadFromText(text: string): void {
    try {
        const raw = JSON.parse(text);
        const payload = parseIpaCliPayload(raw);
        if (!payload) {
            state.ipaError = 'JSON no compatible con el esquema IPA.';
            state.ipaPayload = null;
        } else {
            state.ipaPayload = payload;
            state.ipaError = null;
        }
    } catch (err) {
        state.ipaError = err instanceof Error ? err.message : 'No se pudo leer el JSON.';
        state.ipaPayload = null;
    }
}

// ============================================================================
// Render Functions
// ============================================================================

function renderRecordingState(): void {
    const timerEl = document.getElementById('recording-timer');
    if (timerEl) {
        timerEl.textContent = state.recordingSeconds.toFixed(1) + 's';
    }

    // Animate waveform
    const bars = document.querySelectorAll('.wave-bar');
    bars.forEach((bar, i) => {
        const height = 20 + Math.random() * 60;
        (bar as HTMLElement).style.height = `${height}%`;
    });
}

function renderHeader(): string {
    return `
    <header class="header">
      <div class="header-left">
        <select id="lang-select" class="select-control" value="${state.lang}">
          <option value="es" ${state.lang === 'es' ? 'selected' : ''}>🇪🇸 Español</option>
          <option value="en" ${state.lang === 'en' ? 'selected' : ''}>🇺🇸 English</option>
          <option value="fr" ${state.lang === 'fr' ? 'selected' : ''}>🇫🇷 Français</option>
          <option value="de" ${state.lang === 'de' ? 'selected' : ''}>🇩🇪 Deutsch</option>
        </select>
      </div>
      <h1 class="header-title">PronunciaPA</h1>
      <div class="header-right">
        <div class="stats-mini">
          <span class="level-badge">Lvl ${stats.level}</span>
          <span class="streak-badge">🔥${stats.streak}</span>
        </div>
      </div>
    </header>
  `;
}

function renderModeSelector(): string {
    return `
    <div class="mode-selector">
      <button 
        class="mode-btn ${state.mode === 'phonemic' ? 'active' : ''}" 
        data-mode="phonemic"
      >
        /fonémico/
      </button>
      <button 
        class="mode-btn ${state.mode === 'phonetic' ? 'active' : ''}" 
        data-mode="phonetic"
      >
        [fonético]
      </button>
    </div>
  `;
}

function renderCompareModeSelector(): string {
    const helperByMode: Record<CompareMode, string> = {
        casual: 'Comparacion permisiva para practica diaria.',
        objective: 'Balance entre precision y consistencia.',
        phonetic: 'IPA general para practicar sonidos. Sin pack puede tener baja confiabilidad.',
    };

    return `
    <div class="option-card">
      <label class="label">🔍 Modo de comparacion</label>
      <div class="mode-selector">
        <button
          class="mode-btn ${state.compareMode === 'casual' ? 'active' : ''}"
          data-compare-mode="casual"
        >
          Casual
        </button>
        <button
          class="mode-btn ${state.compareMode === 'objective' ? 'active' : ''}"
          data-compare-mode="objective"
        >
          Objetivo
        </button>
        <button
          class="mode-btn ${state.compareMode === 'phonetic' ? 'active' : ''}"
          data-compare-mode="phonetic"
        >
          IPA general
        </button>
      </div>
      <p class="helper-text">${helperByMode[state.compareMode]}</p>
    </div>
  `;
}

function renderIpaImport(): string {
    const payload = state.ipaPayload;
    const examples = getIpaExamples(payload);
    const summary = state.ipaError ? state.ipaError : getIpaSummary(payload);
    const warnings = payload?.warnings || [];
    const confidence = payload?.confidence;
    const warningHtml = warnings.length
        ? `<p class="ipa-alert">${warnings.join(' ')}</p>`
        : '';
    const confidenceHtml = confidence
        ? `<p class="ipa-meta">Confiabilidad: ${confidence}</p>`
        : '';
    const examplesHtml = examples.length
        ? `
      <div class="ipa-example-list">
        ${examples.map((example, idx) => `
          <button class="ipa-example" data-ipa-example="${idx}">
            <span class="ipa-example-text">${example.text || '-'}</span>
            <span class="ipa-example-meta">${example.ipa || ''}</span>
          </button>
        `).join('')}
      </div>
    `
        : '<p class="helper-text">Carga un JSON del CLI para ver ejemplos.</p>';

    return `
    <div class="option-card">
      <label class="label">📥 Set IPA (CLI JSON)</label>
      <input id="ipa-json-file" type="file" accept="application/json" class="file-input" />
      <textarea id="ipa-json-text" class="ipa-json-textarea" rows="4" placeholder="Pega JSON del CLI aqui..."></textarea>
      <div class="ipa-import-actions">
        <button id="ipa-json-import" class="secondary-btn">Importar texto</button>
        <button id="ipa-json-clear" class="secondary-btn" ${payload ? '' : 'disabled'}>Limpiar</button>
      </div>
      <p class="helper-text">${summary}</p>
      ${warningHtml}
      ${confidenceHtml}
      ${examplesHtml}
    </div>
  `;
}

function renderFeedbackLevelSelector(): string {
    return `
    <div class="option-card">
      <label class="label">💬 Nivel de explicacion</label>
      <div class="mode-selector feedback-selector">
        <button
          class="mode-btn ${state.feedbackLevel === 'casual' ? 'active' : ''}"
          data-feedback-level="casual"
        >
          Amigable
        </button>
        <button
          class="mode-btn ${state.feedbackLevel === 'precise' ? 'active' : ''}"
          data-feedback-level="precise"
        >
          Tecnico
        </button>
      </div>
      <p class="helper-text">El nivel tecnico usa mas detalle fonetico.</p>
    </div>
  `;
}

function renderReferenceInput(): string {
    return `
    <div class="reference-section">
      <label for="reference-text" class="label">📝 Texto de Referencia</label>
      <input 
        type="text" 
        id="reference-text" 
        class="text-input"
        placeholder="Escribe la palabra o frase que quieres practicar..."
        value="${state.referenceText}"
      />
    </div>
  `;
}

function renderRecordButton(): string {
    if (state.isRecording) {
        return `
      <div class="record-section recording">
        <div class="recording-indicator">
          <span class="rec-dot"></span>
          <span id="recording-timer">${state.recordingSeconds.toFixed(1)}s</span>
        </div>
        <div class="waveform">
          ${Array(8).fill(0).map(() => '<div class="wave-bar"></div>').join('')}
        </div>
        <button id="stop-btn" class="record-btn stop">
          <span class="stop-icon">⬛</span>
        </button>
        <p class="record-hint">Toca para detener</p>
      </div>
    `;
    }

    if (state.isProcessing) {
        return `
      <div class="record-section processing">
        <div class="spinner"></div>
        <p class="record-hint">Procesando...</p>
      </div>
    `;
    }

    return `
    <div class="record-section">
      <button id="record-btn" class="record-btn" ${!state.referenceText ? 'disabled' : ''}>
        <span class="mic-icon">🎤</span>
      </button>
      <p class="record-hint">${state.referenceText ? 'Toca para grabar' : 'Primero escribe un texto'}</p>
    </div>
  `;
}

function renderResults(): string {
    if (!state.lastResult) {
        return `
      <div class="results-section empty">
        <p>Graba tu voz para ver resultados</p>
      </div>
    `;
    }

    const result = state.lastResult;
    const score = 1 - (result.per || 0);
    const scorePct = Math.floor(score * 100);
    const scoreColor = getScoreColor(score);

    let message = '';
    if (score >= 0.9) message = '¡Excelente! 🎉';
    else if (score >= 0.7) message = '¡Buen trabajo! 👍';
    else if (score >= 0.5) message = 'Sigue practicando 💪';
    else message = 'Necesitas más práctica 📚';

    // Build alignment display
    const alignment = result.alignment || [];
    const alignmentHtml = alignment.map(([ref, hyp]) => {
        let opType = 'eq';
        if (ref === hyp) opType = 'eq';
        else if (ref === null) opType = 'ins';
        else if (hyp === null) opType = 'del';
        else opType = 'sub';

        return `
      <span class="token op-${opType}" title="${opType}">
        <span class="ref">${ref || '-'}</span>
        <span class="hyp">${hyp || '-'}</span>
      </span>
    `;
    }).join('');

    return `
    <div class="results-section">
      <h3>📊 Resultados</h3>
      
      <div class="score-display">
        <div class="score-value" style="color: ${scoreColor}">${scorePct}%</div>
        <div class="score-bar">
          <div class="score-fill" style="width: ${scorePct}%; background: ${scoreColor}"></div>
        </div>
        <div class="score-message">${message}</div>
      </div>
      
      <div class="alignment-display">
        <div class="alignment-header">
          <span class="legend"><span class="dot op-eq"></span> Match</span>
          <span class="legend"><span class="dot op-sub"></span> Sustitución</span>
          <span class="legend"><span class="dot op-del"></span> Omisión</span>
          <span class="legend"><span class="dot op-ins"></span> Inserción</span>
        </div>
        <div class="alignment-tokens">
          ${alignmentHtml}
        </div>
      </div>
    </div>
  `;
}

function renderFeedbackPanel(): string {
    const feedback = state.lastFeedback?.feedback;
    const report = state.lastFeedback?.report;
    const notice = buildFeedbackNotice(report, feedback);

    let content = '';
    if (state.isFeedbackLoading) {
        content = '<p class="feedback-status">Generando feedback...</p>';
    } else if (state.feedbackError) {
        content = `<p class="feedback-error">${state.feedbackError}</p>`;
    } else if (!feedback) {
        content = '<p class="feedback-status">Graba tu voz para generar feedback</p>';
    } else {
        const drills = feedback.drills || [];
        const drillsHtml = drills.length
            ? drills.map((drill: any) => `<span class="feedback-pill">${formatDrillLabel(drill)}</span>`).join('')
            : '<span class="feedback-empty">Sin drills disponibles.</span>';
        content = `
        <div class="feedback-block">
          <p class="feedback-label">Resumen</p>
          <p class="feedback-text">${feedback.summary || '-'}</p>
        </div>
        <div class="feedback-block">
          <p class="feedback-label">Consejo</p>
          <p class="feedback-text">${feedback.advice_short || '-'}</p>
        </div>
        <div class="feedback-block">
          <p class="feedback-label">Detalle</p>
          <p class="feedback-text">${feedback.advice_long || '-'}</p>
        </div>
        <div class="feedback-block">
          <p class="feedback-label">Drills</p>
          <div class="feedback-drills">${drillsHtml}</div>
        </div>
      `;
    }

    return `
    <div class="feedback-section">
      <h3>💬 Feedback</h3>
      ${notice ? `<div class="feedback-notice">${notice}</div>` : ''}
      ${content}
    </div>
  `;
}

function renderStats(): string {
    const xpPercent = (stats.xp / stats.xpToNextLevel) * 100;

    return `
    <div class="stats-section">
      <h3>🏆 Tu Progreso</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${stats.level}</div>
          <div class="stat-label">${getLevelName(stats.level)}</div>
          <div class="xp-bar">
            <div class="xp-fill" style="width: ${xpPercent}%"></div>
          </div>
          <div class="xp-text">${stats.xp}/${stats.xpToNextLevel} XP</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.totalPractices}</div>
          <div class="stat-label">Prácticas</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${Math.round(stats.avgScore * 100)}%</div>
          <div class="stat-label">Promedio</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">🔥${stats.streak}</div>
          <div class="stat-label">Racha</div>
        </div>
      </div>
    </div>
  `;
}

function renderError(): string {
    if (!state.error) return '';
    return `
    <div class="error-banner">
      <span>❌ ${state.error}</span>
      <button id="dismiss-error" class="dismiss-btn">✕</button>
    </div>
  `;
}

function render(): void {
    const app = document.getElementById('practice-app');
    if (!app) return;

    app.innerHTML = `
    ${renderHeader()}
    <main class="main-content">
      <div class="practice-column">
        ${renderModeSelector()}
        ${renderCompareModeSelector()}
        ${renderIpaImport()}
        ${renderFeedbackLevelSelector()}
        ${renderReferenceInput()}
        ${renderRecordButton()}
      </div>
      <div class="results-column">
        ${renderResults()}
        ${renderFeedbackPanel()}
        ${renderStats()}
      </div>
    </main>
    ${renderError()}
  `;

    attachEventListeners();
}

function attachEventListeners(): void {
    // Language selector
    document.getElementById('lang-select')?.addEventListener('change', (e) => {
        state.lang = (e.target as HTMLSelectElement).value;
        savePreferences();
    });

    // Mode buttons
    document.querySelectorAll('[data-mode]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = (e.target as HTMLElement).dataset.mode as TranscriptionMode;
            if (!mode) return;
            state.mode = mode;
            savePreferences();
            render();
        });
    });

    // Feedback level buttons
    document.querySelectorAll('[data-feedback-level]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const level = (e.target as HTMLElement).dataset.feedbackLevel as FeedbackLevel;
            if (!level) return;
            state.feedbackLevel = level;
            savePreferences();
            render();
        });
    });

    // Compare mode buttons
    document.querySelectorAll('[data-compare-mode]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = (e.target as HTMLElement).dataset.compareMode as CompareMode;
            if (!mode) return;
            state.compareMode = mode;
            savePreferences();
            render();
        });
    });

    // IPA JSON import
    document.getElementById('ipa-json-file')?.addEventListener('change', async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;
        try {
            const text = await file.text();
            loadIpaPayloadFromText(text);
        } catch (err) {
            state.ipaError = err instanceof Error ? err.message : 'No se pudo leer el JSON.';
            state.ipaPayload = null;
        }
        render();
    });

    document.getElementById('ipa-json-import')?.addEventListener('click', () => {
        const textarea = document.getElementById('ipa-json-text') as HTMLTextAreaElement | null;
        const rawText = textarea?.value?.trim() ?? '';
        if (!rawText) {
            state.ipaError = 'Pega un JSON valido para importar.';
            state.ipaPayload = null;
            render();
            return;
        }
        loadIpaPayloadFromText(rawText);
        render();
    });

    document.getElementById('ipa-json-clear')?.addEventListener('click', () => {
        state.ipaPayload = null;
        state.ipaError = null;
        const fileInput = document.getElementById('ipa-json-file') as HTMLInputElement | null;
        if (fileInput) fileInput.value = '';
        const textarea = document.getElementById('ipa-json-text') as HTMLTextAreaElement | null;
        if (textarea) textarea.value = '';
        render();
    });

    // IPA example selection
    document.querySelectorAll('[data-ipa-example]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = Number((e.currentTarget as HTMLElement).dataset.ipaExample);
            const examples = getIpaExamples(state.ipaPayload);
            const example = examples[index];
            if (!example?.text) return;
            state.referenceText = example.text;
            render();
        });
    });

    // Reference text
    document.getElementById('reference-text')?.addEventListener('input', (e) => {
        state.referenceText = (e.target as HTMLInputElement).value;
        // Re-render to update button state
        const btn = document.getElementById('record-btn');
        if (btn) {
            (btn as HTMLButtonElement).disabled = !state.referenceText;
        }
    });

    // Record button
    document.getElementById('record-btn')?.addEventListener('click', () => {
        if (state.referenceText) {
            startRecording();
        }
    });

    // Stop button
    document.getElementById('stop-btn')?.addEventListener('click', () => {
        processRecording();
    });

    // Dismiss error
    document.getElementById('dismiss-error')?.addEventListener('click', () => {
        state.error = null;
        render();
    });
}

// ============================================================================
// Initialize
// ============================================================================

export function initPractice(): void {
    loadPreferences();

    // Create app container if needed
    let app = document.getElementById('practice-app');
    if (!app) {
        app = document.createElement('div');
        app.id = 'practice-app';
        app.className = 'practice-app';
        document.body.appendChild(app);
    }

    render();
}

// Auto-init if DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPractice);
} else {
    initPractice();
}
