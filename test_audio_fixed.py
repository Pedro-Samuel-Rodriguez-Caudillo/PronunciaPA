"""Test endpoint de audio con URL encoding."""
import requests
from urllib.parse import quote
import time

time.sleep(1)

try:
    # Probar con URL encoding
    sound_id = "es/ɾ"
    encoded_id = quote(sound_id, safe='/')  # Keep the slash
    print(f"Testing: {encoded_id}")
    
    response = requests.get(f"http://127.0.0.1:8000/api/ipa-sounds/{encoded_id}/audio", timeout=30)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        print(f"X-Example-Text: {response.headers.get('X-Example-Text')}")
        print(f"X-Sound-IPA: {response.headers.get('X-Sound-IPA')}")
        with open("test_audio.wav", "wb") as f:
            f.write(response.content)
        print(f"✓ Audio guardado ({len(response.content)} bytes)")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
