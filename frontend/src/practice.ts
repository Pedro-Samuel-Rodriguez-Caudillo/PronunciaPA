/**
 * PronunciaPA Practice Page
 * Interactive pronunciation practice with recording, real-time feedback, and gamification
 */

import { createApiClient, type CompareRequest } from './api';
import type { CompareResponse, FeedbackResponse } from './types/api';

// ============================================================================
// Types
// ============================================================================

type TranscriptionMode = 'phonemic' | 'phonetic';
type FeedbackLevel = 'casual' | 'precise';

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
    referenceText: string;
    isRecording: boolean;
    isProcessing: boolean;
    recordingSeconds: number;
    lastResult: CompareResponse | null;
    lastFeedback: FeedbackResponse | null;
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

// ============================================================================
// State
// ============================================================================

let state: SessionState = {
    lang: 'es',
    mode: 'phonemic',
    feedbackLevel: 'casual',
    referenceText: '',
    isRecording: false,
    isProcessing: false,
    recordingSeconds: 0,
    lastResult: null,
    lastFeedback: null,
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
    state.error = null;
    render();

    try {
        const result = await api.compare({
            audio: audioBlob,
            text: state.referenceText,
            lang: state.lang,
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
        ${renderReferenceInput()}
        ${renderRecordButton()}
      </div>
      <div class="results-column">
        ${renderResults()}
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
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = (e.target as HTMLElement).dataset.mode as TranscriptionMode;
            state.mode = mode;
            savePreferences();
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
