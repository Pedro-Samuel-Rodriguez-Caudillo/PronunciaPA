"""Test endpoint de audio TTS."""
import requests
import time

# Esperar un poco
time.sleep(1)

try:
    # Probar endpoint de audio
    sound_id = "es/ɾ"
    response = requests.get(f"http://127.0.0.1:8000/api/ipa-sounds/{sound_id}/audio", timeout=30)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"X-Example-Text: {response.headers.get('X-Example-Text')}")
    print(f"X-Sound-IPA: {response.headers.get('X-Sound-IPA')}")
    
    if response.status_code == 200:
        # Guardar el audio
        with open("test_audio.wav", "wb") as f:
            f.write(response.content)
        print(f"Audio guardado en test_audio.wav ({len(response.content)} bytes)")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
