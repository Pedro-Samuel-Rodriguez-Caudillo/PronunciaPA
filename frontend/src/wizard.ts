/**
 * Setup Wizard - Verifica y ayuda a instalar dependencias del sistema
 */

export interface SetupCheck {
  installed: boolean;
  version?: string;
  path?: string;
  running?: boolean;
  models?: string[];
  instructions?: {
    command?: string;
    commands?: string[];
    url?: string;
    description: string;
    env_var?: string;
  } | null;
}

export interface SetupStatus {
  os: string;
  strict_mode: boolean;
  checks: {
    allosaurus?: SetupCheck;
    espeak?: SetupCheck;
    ollama?: SetupCheck;
    models_script?: SetupCheck;
  };
}

export interface ComponentHealth {
  name: string;
  ready: boolean;
  error?: string;
  output_type?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  strict_mode: boolean;
  components: {
    asr: ComponentHealth;
    textref: ComponentHealth;
    llm?: ComponentHealth;
    tts?: ComponentHealth;
  };
  language_packs: string[];
  local_models: number;
}

/**
 * Cliente para APIs de setup
 */
export class SetupClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}

  async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getSetupStatus(): Promise<SetupStatus> {
    const response = await fetch(`${this.baseUrl}/api/setup-status`);
    if (!response.ok) {
      throw new Error(`Setup status failed: ${response.statusText}`);
    }
    return response.json();
  }

  async runCommand(command: string): Promise<{ success: boolean; output: string; error?: string }> {
    // Por ahora, solo mostramos comandos para copiar
    // En el futuro podríamos implementar ejecución vía Electron/Tauri
    return {
      success: false,
      output: '',
      error: 'Automatic command execution not implemented yet. Please run manually.',
    };
  }
}

/**
 * Renderiza el wizard de setup en el DOM
 */
export class SetupWizard {
  private client: SetupClient;
  private container: HTMLElement;

  constructor(containerId: string, baseUrl?: string) {
    const el = document.getElementById(containerId);
    if (!el) {
      throw new Error(`Container element #${containerId} not found`);
    }
    this.container = el;
    this.client = new SetupClient(baseUrl);
  }

  async show(): Promise<void> {
    this.container.classList.remove('hidden');
    await this.render();
  }

  hide(): void {
    this.container.classList.add('hidden');
  }

  private async render(): Promise<void> {
    this.container.innerHTML = `
      <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div class="p-6">
            <div class="flex justify-between items-center mb-6">
              <h2 class="text-2xl font-bold text-gray-900">Configuración del Sistema</h2>
              <button id="closeWizard" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div id="wizardContent" class="space-y-6">
              <div class="text-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p class="mt-4 text-gray-600">Verificando estado del sistema...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const closeBtn = document.getElementById('closeWizard');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }

    try {
      const [health, setupStatus] = await Promise.all([
        this.client.checkHealth(),
        this.client.getSetupStatus(),
      ]);

      await this.renderContent(health, setupStatus);
    } catch (error) {
      this.renderError(error);
    }
  }

  private async renderContent(health: HealthResponse, setup: SetupStatus): Promise<void> {
    const contentEl = document.getElementById('wizardContent');
    if (!contentEl) return;

    const hasIssues = this.detectIssues(health, setup);

    if (!hasIssues) {
      contentEl.innerHTML = `
        <div class="text-center py-8">
          <svg class="w-16 h-16 text-green-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">¡Sistema Listo!</h3>
          <p class="text-gray-600">Todos los componentes están instalados y funcionando correctamente.</p>
        </div>
      `;
      return;
    }

    let html = `
      <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm text-yellow-700">
              Se detectaron componentes faltantes o no configurados. Sigue las instrucciones para completar la instalación.
            </p>
          </div>
        </div>
      </div>
      
      <div class="space-y-4">
    `;

    // Sección: ASR Backend
    const asr = health.components.asr;
    html += this.renderCheckSection(
      'Backend ASR (Allosaurus)',
      asr.ready,
      asr.error,
      setup.checks.allosaurus
    );

    // Sección: TextRef (eSpeak)
    const textref = health.components.textref;
    html += this.renderCheckSection(
      'TextRef Provider (eSpeak-NG)',
      textref.ready,
      textref.error,
      setup.checks.espeak
    );

    // Sección: LLM (Ollama) - opcional
    if (health.components.llm) {
      const llm = health.components.llm;
      html += this.renderCheckSection(
        'LLM Provider (Ollama) - Opcional',
        llm.ready,
        llm.error,
        setup.checks.ollama
      );
    }

    // Sección: Descarga de modelos
    if (setup.checks.models_script) {
      html += this.renderCheckSection(
        'Modelos de Allosaurus',
        false,
        'Ejecuta el script para descargar los modelos necesarios',
        setup.checks.models_script
      );
    }

    html += `
      </div>
      <div class="mt-6 pt-6 border-t border-gray-200">
        <p class="text-sm text-gray-600">
          <strong>Sistema operativo:</strong> ${setup.os}<br>
          <strong>Modo estricto:</strong> ${setup.strict_mode ? 'Activado' : 'Desactivado'}
        </p>
      </div>
    `;

    contentEl.innerHTML = html;

    // Agregar event listeners para botones de copiar
    this.attachCopyListeners();
  }

  private renderCheckSection(
    title: string,
    ready: boolean,
    error: string | undefined,
    check: SetupCheck | undefined
  ): string {
    const statusIcon = ready
      ? `<svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
         </svg>`
      : `<svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
         </svg>`;

    let html = `
      <div class="border rounded-lg p-4 ${ready ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}">
        <div class="flex items-start">
          <div class="flex-shrink-0">${statusIcon}</div>
          <div class="ml-3 flex-1">
            <h3 class="text-sm font-medium ${ready ? 'text-green-800' : 'text-red-800'}">${title}</h3>
    `;

    if (ready) {
      html += `<p class="mt-1 text-sm text-green-700">✓ Instalado y funcionando</p>`;
      if (check?.version) {
        html += `<p class="text-xs text-green-600 mt-1">Versión: ${check.version}</p>`;
      }
      if (check?.path) {
        html += `<p class="text-xs text-green-600 mt-1">Ruta: ${check.path}</p>`;
      }
    } else {
      if (error) {
        html += `<p class="mt-1 text-sm text-red-700">${error}</p>`;
      }

      if (check?.instructions) {
        const inst = check.instructions;
        html += `<div class="mt-3 p-3 bg-white rounded border border-gray-200">`;
        html += `<p class="text-sm text-gray-700 mb-2"><strong>${inst.description}</strong></p>`;

        if (inst.url) {
          html += `<p class="text-sm mb-2">
            <a href="${inst.url}" target="_blank" class="text-blue-600 hover:underline">
              ${inst.url} ↗
            </a>
          </p>`;
        }

        if (inst.command) {
          html += this.renderCommandBox(inst.command);
        }

        if (inst.commands) {
          inst.commands.forEach((cmd) => {
            if (cmd.startsWith('#')) {
              html += `<p class="text-sm text-gray-600 mt-2">${cmd}</p>`;
            } else {
              html += this.renderCommandBox(cmd);
            }
          });
        }

        if (inst.env_var) {
          html += `<p class="text-xs text-gray-600 mt-2">Variable de entorno: <code class="bg-gray-100 px-1 py-0.5 rounded">${inst.env_var}</code></p>`;
        }

        html += `</div>`;
      }
    }

    html += `
          </div>
        </div>
      </div>
    `;

    return html;
  }

  private renderCommandBox(command: string): string {
    const cmdId = `cmd_${Math.random().toString(36).substring(2, 9)}`;
    return `
      <div class="mt-2 flex items-center bg-gray-900 text-white rounded p-2 font-mono text-sm">
        <code class="flex-1 overflow-x-auto" id="${cmdId}">${this.escapeHtml(command)}</code>
        <button class="ml-2 px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs copy-btn" data-target="${cmdId}">
          Copiar
        </button>
      </div>
    `;
  }

  private attachCopyListeners(): void {
    document.querySelectorAll('.copy-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const target = (e.target as HTMLElement).dataset.target;
        if (!target) return;
        
        const codeEl = document.getElementById(target);
        if (!codeEl) return;
        
        const text = codeEl.textContent || '';
        navigator.clipboard.writeText(text).then(() => {
          const btnEl = e.target as HTMLElement;
          const originalText = btnEl.textContent;
          btnEl.textContent = '✓ Copiado';
          setTimeout(() => {
            btnEl.textContent = originalText;
          }, 2000);
        });
      });
    });
  }

  private detectIssues(health: HealthResponse, setup: SetupStatus): boolean {
    // Verificar componentes críticos
    if (!health.components.asr.ready) return true;
    if (!health.components.textref.ready) return true;
    
    // Verificar instalaciones
    if (setup.checks.allosaurus && !setup.checks.allosaurus.installed) return true;
    if (setup.checks.espeak && !setup.checks.espeak.installed) return true;
    
    return false;
  }

  private renderError(error: any): void {
    const contentEl = document.getElementById('wizardContent');
    if (!contentEl) return;

    contentEl.innerHTML = `
      <div class="text-center py-8">
        <svg class="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">Error al verificar el sistema</h3>
        <p class="text-gray-600">${this.escapeHtml(error.message || 'Error desconocido')}</p>
        <button id="retryBtn" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Reintentar
        </button>
      </div>
    `;

    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => this.render());
    }
  }

  private escapeHtml(unsafe: string): string {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}
