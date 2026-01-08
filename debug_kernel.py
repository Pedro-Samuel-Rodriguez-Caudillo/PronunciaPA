import asyncio
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel

async def main():
    print("Loading config...")
    cfg = loader.load_config()
    print("Creating kernel...")
    kernel = create_kernel(cfg)
    
    print("Setup...")
    await kernel.setup()
    
    try:
        print("Running compare...")
        # create a dummy wav file if not exists
        import os
        if not os.path.exists("test.wav"):
            with open("test.wav", "wb") as f:
                f.write(b'\x00' * 1024)
                
        audio_in = {"path": "test.wav", "sample_rate": 16000, "channels": 1}
        res = await kernel.run(audio=audio_in, text="hola")
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        print("Teardown...")
        await kernel.teardown()

if __name__ == "__main__":
    asyncio.run(main())
