import React from 'react';

interface RecordButtonProps {
  isRecording: boolean;
  isProcessing?: boolean;
  disabled?: boolean;
  onClick: () => void;
  size?: number;
}

export const RecordButton: React.FC<RecordButtonProps> = ({
  isRecording,
  isProcessing = false,
  disabled = false,
  onClick,
  size = 80,
}) => {
  return (
    <button
      className="btn-record"
      data-recording={isRecording}
      onClick={onClick}
      disabled={disabled || isProcessing}
      style={{ width: size, height: size }}
      aria-label={
        isRecording
          ? 'Detener grabación'
          : isProcessing
            ? 'Procesando...'
            : 'Iniciar grabación'
      }
      aria-pressed={isRecording}
      role="button"
    >
      {isProcessing && (
        <span
          className="spinner"
          style={{
            position: 'absolute',
            zIndex: 2,
            width: size * 0.3,
            height: size * 0.3,
          }}
        />
      )}
    </button>
  );
};
