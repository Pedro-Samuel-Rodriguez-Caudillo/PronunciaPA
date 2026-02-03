"""Test endpoint de audio con query parameter."""
import requests
from urllib.parse import quote

sound_id = "es/r"  # Probar con un sonido simple primero
url = f"http://127.0.0.1:8000/api/ipa-sounds/audio?sound_id={quote(sound_id)}"

print(f"Testing: {url}")

try:
    response = requests.get(url, timeout=30)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        print(f"X-Example-Text: {response.headers.get('X-Example-Text')}")
        print(f"X-Sound-IPA: {response.headers.get('X-Sound-IPA')}")
        with open("test_audio_r.wav", "wb") as f:
            f.write(response.content)
        print(f"✓ Audio guardado ({len(response.content)} bytes)")
    else:
        print(f"Error: {response.json()}")
        
except Exception as e:
    print(f"Error: {e}")
