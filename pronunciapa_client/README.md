# PronunciaPA Mobile Client

Cliente móvil Flutter para PronunciaPA - evaluación de pronunciación en cualquier idioma.

## Requisitos

- Flutter SDK ^3.5.4
- Dart SDK ^3.5.4
- Android Studio o Xcode (para iOS)

## Instalación

```bash
cd pronunciapa_client
flutter pub get
```

## Ejecución

```bash
# Android
flutter run -d android

# iOS (requiere macOS)
flutter run -d ios

# Web
flutter run -d chrome
```

## Configuración del Backend

El cliente se conecta a la API de PronunciaPA. Configura la URL del backend en `lib/data/api_client.dart`:

```dart
const String apiBaseUrl = 'http://localhost:8000';
```

Para producción, usa la URL del servidor desplegado.

## Arquitectura

```
lib/
├── data/           # Capa de datos (API, modelos)
├── domain/         # Lógica de negocio
├── presentation/   # UI (widgets, pantallas)
└── main.dart       # Punto de entrada
```

## Dependencias principales

- **flutter_riverpod**: Gestión de estado
- **http**: Cliente HTTP para API
- **record**: Grabación de audio
- **path_provider**: Rutas de sistema
- **permission_handler**: Permisos de micrófono

## Estado

⚠️ **Alpha** - En desarrollo activo. La API puede cambiar.

## Licencia

MIT - Ver [LICENSE](../LICENSE) en la raíz del proyecto.
