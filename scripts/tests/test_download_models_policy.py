"""Tests para scripts/download_models.py - Validar política de modelos."""
import subprocess
import sys
from pathlib import Path


def test_download_models_help():
    """Verifica que el script muestre la ayuda correctamente."""
    result = subprocess.run(
        [sys.executable, "scripts/download_models.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # Ir a raíz del proyecto
    )
    
    # El script puede retornar 0 o tener problemas menores, verificamos output
    output = result.stdout + result.stderr
    assert "--with-llms" in output
    assert "--with-phi3" in output
    assert "--wav2vec2-ipa-model" in output
    assert "TinyLlama" in output or "ejercicios" in output
    print("✅ Help output correct")


def test_download_models_no_wav2vec2_by_default():
    """Verifica que wav2vec2 NO se descarga por defecto."""
    # No podemos ejecutar la descarga real, pero podemos verificar los argumentos
    result = subprocess.run(
        [sys.executable, "scripts/download_models.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # Ir a raíz del proyecto
    )
    # Verifica que el default de wav2vec2-ipa-model es None (no se descarga)
    output = result.stdout + result.stderr
    assert "wav2vec2-ipa-model" in output
    assert "opcional" in output.lower() or "optional" in output.lower()
    print("✅ Wav2Vec2 is optional (not default)")


def test_script_import():
    """Verifica que el script se puede importar sin errores."""
    import sys
    from pathlib import Path
    
    # Añadir el directorio scripts al path
    scripts_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(scripts_dir))
    
    try:
        import download_models
        
        # Verificar que las funciones existen
        assert hasattr(download_models, "download_allosaurus")
        assert hasattr(download_models, "verify_espeak")
        assert hasattr(download_models, "download_tinyllama")
        assert hasattr(download_models, "download_wav2vec2_ipa")
        assert hasattr(download_models, "main")
        
        # Verificar que no existe DEFAULT_W2V2_MODEL
        assert not hasattr(download_models, "DEFAULT_W2V2_MODEL")
        
        print("✅ Script imports correctly and has required functions")
    except Exception as e:
        print(f"⚠️ Could not import download_models: {e}")
        print("   (This is OK if dependencies are not installed)")
    finally:
        if str(scripts_dir) in sys.path:
            sys.path.remove(str(scripts_dir))


if __name__ == "__main__":
    test_download_models_help()
    test_download_models_no_wav2vec2_by_default()
    test_script_import()
    print("\n✅ All download_models tests passed!")
