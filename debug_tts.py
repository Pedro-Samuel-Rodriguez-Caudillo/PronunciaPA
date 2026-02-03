"""Depuración del error TTS."""
import asyncio
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel

async def test_tts():
    try:
        cfg = loader.load_config()
        kernel = create_kernel(cfg)
        await kernel.setup()
        
        result = await kernel.tts.synthesize(
            text="rojo",
            lang="es",
            output_path="debug_audio.wav",
        )
        
        print(f"Success: {result}")
        await kernel.teardown()
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print("\nTraceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts())
