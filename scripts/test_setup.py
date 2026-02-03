#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el sistema está funcionando.

Este script demuestra:
1. Carga de configuración con strict_mode
2. Creación del kernel con auto-fallback
3. Health check del servidor
4. Setup status endpoint
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_config():
    """Prueba 1: Cargar configuración"""
    print("=" * 60)
    print("PRUEBA 1: Carga de Configuración")
    print("=" * 60)
    
    from ipa_core.config import loader
    
    cfg = loader.load_config()
    print(f"✅ Configuración cargada exitosamente")
    print(f"   - Versión schema: {cfg.version}")
    print(f"   - Strict mode: {cfg.strict_mode}")
    print(f"   - Backend ASR: {cfg.backend.name}")
    print(f"   - TextRef: {cfg.textref.name}")
    print(f"   - Comparator: {cfg.comparator.name}")
    print()
    return cfg


async def test_kernel(cfg):
    """Prueba 2: Crear kernel con auto-fallback"""
    print("=" * 60)
    print("PRUEBA 2: Creación del Kernel")
    print("=" * 60)
    
    from ipa_core.kernel.core import create_kernel
    
    kernel = create_kernel(cfg)
    print(f"✅ Kernel creado exitosamente")
    print(f"   - ASR: {type(kernel.asr).__name__}")
    print(f"   - TextRef: {type(kernel.textref).__name__}")
    print(f"   - Comparator: {type(kernel.comp).__name__}")
    print(f"   - Preprocessor: {type(kernel.pre).__name__}")
    print()
    
    # Setup
    await kernel.setup()
    print("✅ Setup completado")
    print()
    
    return kernel


async def test_health():
    """Prueba 3: Verificar endpoint /health"""
    print("=" * 60)
    print("PRUEBA 3: Health Check del Servidor")
    print("=" * 60)
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/health", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Servidor respondiendo correctamente")
                print(f"   - Status: {data.get('status')}")
                print(f"   - Version: {data.get('version')}")
                print(f"   - Strict mode: {data.get('strict_mode')}")
                print(f"   - Componentes:")
                for name, info in data.get('components', {}).items():
                    ready = "✅" if info.get('ready') else "❌"
                    print(f"     {ready} {name}: {info.get('name')}")
                    if not info.get('ready') and info.get('error'):
                        print(f"        Error: {info['error'][:80]}...")
                print()
            else:
                print(f"⚠️  Servidor respondió con status {resp.status_code}")
    except Exception as e:
        print(f"⚠️  No se pudo conectar al servidor: {e}")
        print(f"   Asegúrate de que el servidor esté corriendo:")
        print(f"   uvicorn ipa_server.main:get_app --reload --port 8000")
        print()


async def test_setup_status():
    """Prueba 4: Verificar endpoint /api/setup-status"""
    print("=" * 60)
    print("PRUEBA 4: Setup Status")
    print("=" * 60)
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/setup-status", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Setup status disponible")
                print(f"   - OS: {data.get('os')}")
                print(f"   - Strict mode: {data.get('strict_mode')}")
                print(f"   - Checks:")
                for name, check in data.get('checks', {}).items():
                    installed = "✅" if check.get('installed') else "❌"
                    print(f"     {installed} {name}")
                    if not check.get('installed') and check.get('instructions'):
                        inst = check['instructions']
                        if 'command' in inst:
                            print(f"        Comando: {inst['command']}")
                        if 'url' in inst:
                            print(f"        URL: {inst['url']}")
                print()
            else:
                print(f"⚠️  Servidor respondió con status {resp.status_code}")
    except Exception as e:
        print(f"⚠️  No se pudo conectar al servidor: {e}")
        print()


async def test_transcription(kernel):
    """Prueba 5: Transcripción básica con stub"""
    print("=" * 60)
    print("PRUEBA 5: Transcripción con Stub")
    print("=" * 60)
    
    # Simular entrada de audio
    audio_input = {
        "path": "test.wav",
        "sample_rate": 16000,
        "channels": 1
    }
    
    try:
        # En modo stub, el ASR retorna fonemas basados en el texto
        result = await kernel.asr.transcribe(audio_input, lang="es")
        print(f"✅ Transcripción exitosa")
        print(f"   - IPA: {result.get('ipa', 'N/A')}")
        print(f"   - Tokens: {result.get('tokens', [])}")
        print(f"   - Meta: {result.get('meta', {})}")
        print()
    except Exception as e:
        print(f"⚠️  Error en transcripción: {e}")
        print()


async def main():
    """Ejecutar todas las pruebas"""
    print("\n")
    print("🧪 SUITE DE PRUEBAS - PronunciaPA")
    print("=" * 60)
    print()
    
    # Prueba 1: Configuración
    cfg = await test_config()
    
    # Prueba 2: Kernel
    kernel = await test_kernel(cfg)
    
    # Prueba 3: Health check (requiere servidor corriendo)
    await test_health()
    
    # Prueba 4: Setup status (requiere servidor corriendo)
    await test_setup_status()
    
    # Prueba 5: Transcripción
    await test_transcription(kernel)
    
    # Resumen
    print("=" * 60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("=" * 60)
    print()
    print("Para probar el sistema completo:")
    print("1. Iniciar servidor: uvicorn ipa_server.main:get_app --reload --port 8000")
    print("2. Abrir frontend: cd frontend && npm run dev")
    print("3. Navegar a: http://localhost:5173")
    print()
    print("El wizard se mostrará automáticamente si faltan componentes.")
    print()
    
    await kernel.teardown()


if __name__ == "__main__":
    asyncio.run(main())
