"""Test simple para verificar endpoints."""
import requests
import time

# Esperar un poco para que el servidor inicie
time.sleep(3)

try:
    # Probar endpoint de sonidos IPA
    response = requests.get("http://127.0.0.1:8000/api/ipa-sounds?lang=es")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total sounds: {data.get('total')}")
        
        # Mostrar primer sonido
        if data.get('sounds'):
            sound = data['sounds'][0]
            print(f"\nFirst sound:")
            print(f"  IPA: {sound.get('ipa')}")
            print(f"  Label: {sound.get('label')}")
            print(f"  Audio URL: {sound.get('audio_url')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Connection error: {e}")
