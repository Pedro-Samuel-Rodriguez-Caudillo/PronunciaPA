"""Ver IDs exactos de los sonidos."""
import requests

response = requests.get("http://127.0.0.1:8000/api/ipa-sounds?lang=es")
if response.status_code == 200:
    data = response.json()
    print("Sonidos disponibles:")
    for sound in data['sounds'][:3]:
        print(f"  ID: {sound['id']}")
        print(f"  IPA: {sound['ipa']}")
        print(f"  Audio URL: {sound['audio_url']}")
        print()
