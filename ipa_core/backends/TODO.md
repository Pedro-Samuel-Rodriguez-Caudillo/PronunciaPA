# TODO - backends

- [ ] Implementar WhisperIPABackend cargando el modelo HF y normalizando a IPA.
- [ ] Integrar una CNN (pre-entrenada o propia) para la extraccion de embeddings acusticos previos a la decodificacion.
- [ ] Permitir configuracion de dispositivo (cpu/gpu) y parametros de inferencia.
- [ ] Agregar manejo de errores para archivos de audio inexistentes o invalidos.
- [ ] Documentar formato de salida esperado del backend (tokenizacion IPA, normalizacion, etc.).
- [ ] Crear pruebas unitarias usando fixtures de audio sintetico.
