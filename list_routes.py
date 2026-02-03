"""Listar todas las rutas disponibles en el servidor."""
import requests

try:
    response = requests.get("http://127.0.0.1:8000/openapi.json")
    if response.status_code == 200:
        data = response.json()
        print("Rutas disponibles:")
        for path in sorted(data.get('paths', {}).keys()):
            print(f"  {path}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
