# PronunciaPA

Estructura principal (sujeta a ajustes durante el diseño):

- `ipa_core/` (núcleo y plugins; sin implementación por ahora)
- `configs/` y `config/` (plantillas vacías con TODOs)
- `scripts/` (sin lógica; TODOs)
- `frontend/` (sin implementación; TODOs)
- `docs/backlog.md` y `**/TODO.md` (únicas fuentes de verdad por ahora)

Arquitectura (mermaid)
----------------------

```mermaid
flowchart LR
    subgraph ipa_core[ipa_core]
        K[Kernel] --> PPR[Preprocessor]
        K --> ASR[ASRBackend]
        K --> TR[TextRefProvider]
        K --> CMP[Comparator]
        subgraph ports[ports]
            PPR
            ASR
            TR
            CMP
        end
        subgraph pipeline[pipeline]
            RUN[runner.run_pipeline]
        end
        subgraph config[config]
            CFG[loader/schema]
        end
        subgraph plugins[plugins]
            REG[registry]
            DISC[discovery]
        end
    end

    CLI[CLI] --> K
    API[(HTTP API)] --> K
    CFG --> K
    REG --> K
    RUN --> K

    AIN[(AudioInput)] --> ASR
    TXT[(Text)] --> TR
    ASR --> CMP
    TR --> CMP
    CMP --> OUT[(CompareResult)]
```
