import wave
import struct

def create_silent_wav(path, duration=1.0, sr=16000):
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        n_frames = int(duration * sr)
        for _ in range(n_frames):
            data = struct.pack('<h', 0)
            f.writeframesraw(data)

create_silent_wav('data/benchmarks/sample.wav')
