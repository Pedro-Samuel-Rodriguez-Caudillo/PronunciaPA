from pathlib import Path
import os

def get_models_dir() -> Path:
    """Retorna la ruta al directorio de modelos locales, creándolo si no existe."""
    home = Path.home()
    model_dir = home / ".pronunciapa" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir

def scan_models() -> list[str]:
    """Escanea el directorio de modelos y retorna una lista de nombres válidos."""
    model_dir = get_models_dir()
    valid_models = []
    
    for item in model_dir.iterdir():
        if item.is_dir() and (item / "config.json").exists():
            valid_models.append(item.name)
            
    return valid_models
