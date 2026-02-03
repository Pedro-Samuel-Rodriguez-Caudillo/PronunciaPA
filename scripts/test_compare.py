"""Script de prueba para verificar el pipeline de comparación."""
import asyncio
from pathlib import Path

async def test_compare():
    import wave
    import struct
    from ipa_core.config import loader
    from ipa_core.kernel.core import create_kernel
    from ipa_core.services.comparison import ComparisonService
    
    cfg = loader.load_config()
    kernel = create_kernel(cfg)
    await kernel.setup()
    
    # Crear archivo de audio de prueba con tono
    test_path = Path('test_tone.wav')
    with wave.open(str(test_path), 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        # 1 segundo de tono 440Hz
        import math
        for i in range(16000):
            sample = int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / 16000))
            f.writeframes(struct.pack('<h', sample))
    
    service = ComparisonService(
        preprocessor=kernel.pre,
        asr=kernel.asr,
        textref=kernel.textref,
        comparator=kernel.comp,
        default_lang='es',
    )
    
    try:
        payload = await service.compare_file_detail(str(test_path), 'hola', lang='es')
        print('hyp_tokens:', payload.hyp_tokens)
        print('ref_tokens:', payload.ref_tokens)
        print('result:', payload.result)
    except Exception as e:
        print('Error:', type(e).__name__, e)
    finally:
        await kernel.teardown()
        if test_path.exists():
            test_path.unlink()

if __name__ == '__main__':
    asyncio.run(test_compare())
