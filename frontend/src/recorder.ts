/**
 * Audio recorder widget using MediaRecorder API
 * Handles microphone permissions, recording, and audio blob creation
 */

export interface RecorderOptions {
  onRecordingComplete: (audioBlob: Blob, audioUrl: string) => void;
  onError?: (error: string) => void;
  mimeType?: string;
}

export class AudioRecorderWidget {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private isRecording = false;
  private options: RecorderOptions;
  
  // UI Elements
  private container: HTMLElement;
  private recordButton: HTMLButtonElement;
  private statusText: HTMLElement;
  private errorText: HTMLElement;

  constructor(containerId: string, options: RecorderOptions) {
    const container = document.getElementById(containerId);
    if (!container) {
      throw new Error(`Container with id "${containerId}" not found`);
    }
    this.container = container;
    this.options = options;
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="audio-recorder">
        <button id="recordButton" class="record-button">
          <svg class="mic-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <span class="button-text">Grabar Audio</span>
        </button>
        <div id="statusText" class="status-text"></div>
        <div id="errorText" class="error-text"></div>
      </div>
    `;

    this.recordButton = this.container.querySelector('#recordButton')!;
    this.statusText = this.container.querySelector('#statusText')!;
    this.errorText = this.container.querySelector('#errorText')!;

    this.recordButton.addEventListener('click', () => {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        this.startRecording();
      }
    });
  }

  private async startRecording(): Promise<void> {
    try {
      this.errorText.textContent = '';
      
      // Request microphone permission
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Determine mime type
      const mimeType = this.options.mimeType || this.getSupportedMimeType();
      
      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
      this.audioChunks = [];

      this.mediaRecorder.addEventListener('dataavailable', (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      });

      this.mediaRecorder.addEventListener('stop', () => {
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);
        this.options.onRecordingComplete(audioBlob, audioUrl);
        
        // Cleanup
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
          this.stream = null;
        }
      });

      this.mediaRecorder.start();
      this.isRecording = true;
      this.updateUI();
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.errorText.textContent = `Error: ${errorMessage}`;
      this.options.onError?.(errorMessage);
    }
  }

  private stopRecording(): void {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
      this.updateUI();
    }
  }

  private updateUI(): void {
    if (this.isRecording) {
      this.recordButton.classList.add('recording');
      this.recordButton.querySelector('.button-text')!.textContent = 'Detener Grabación';
      this.statusText.textContent = '🔴 Grabando...';
      this.statusText.style.color = '#ef4444';
    } else {
      this.recordButton.classList.remove('recording');
      this.recordButton.querySelector('.button-text')!.textContent = 'Grabar Audio';
      this.statusText.textContent = '';
    }
  }

  private getSupportedMimeType(): string {
    const types = [
      'audio/webm',
      'audio/webm;codecs=opus',
      'audio/ogg;codecs=opus',
      'audio/wav',
    ];
    
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    
    return 'audio/webm'; // fallback
  }

  public destroy(): void {
    if (this.isRecording) {
      this.stopRecording();
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
  }
}
