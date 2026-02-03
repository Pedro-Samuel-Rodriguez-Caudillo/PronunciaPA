# PronunciaPA - Modelo de Negocio

## Visión
**Alternativa open-source a ELSA Speak**, ultra-especializada en pronunciación y extensible a cualquier idioma. Con fuerte énfasis en **enseñar IPA** (no solo usarlo internamente).

---

## Segmentos de Mercado

### 🆓 Individuos (B2C Gratuito)
- Estudiantes de idiomas
- Profesionales que necesitan mejorar pronunciación
- Entusiastas de lingüística/IPA
- Inmigrantes aprendiendo nuevo idioma

### 💼 Negocios (B2B de Pago)
- Escuelas de idiomas
- Universidades con programas de lingüística
- Call centers multinacionales
- Empresas con equipos globales
- Editoriales de material educativo

---

## Propuesta de Valor

### Para Individuos (Gratis)
| Feature | Descripción |
|---------|-------------|
| 🎯 Análisis de pronunciación | Grabas → Recibes feedback IPA preciso |
| 📚 Aprender IPA | Tutorial interactivo de símbolos fonéticos |
| 🔊 Audio de referencia | TTS nativo para cada sonido |
| 📊 Drills de práctica | Ejercicios por sonido: aislado, sílaba, palabra |
| 🔄 Pares mínimos | ship/sheep, bit/beat para distinguir sonidos |
| 🌐 Multilingüe | Inglés primero, español, francés, etc. |
| 📱 Offline básico | Funciona sin internet (modelos locales) |

### Para Negocios (Pago)
| Feature | Precio Sugerido |
|---------|-----------------|
| 📊 Dashboard de grupo | Métricas de todos los estudiantes | $99/mes por 50 usuarios |
| 📈 Reportes de progreso | Exportables, por usuario/grupo | Incluido en plan |
| 🎯 Contenido personalizado | Vocabulario/frases específicas del negocio | $299/mes |
| 🔗 API de integración | Embed en LMS (Moodle, Canvas, etc.) | $199/mes base + uso |
| 🏢 White-label | Tu marca, nuestro motor | $999/mes |
| 👥 SSO/SAML | Integración con Active Directory | $149/mes add-on |
| 📞 Soporte prioritario | SLA 24h, onboarding dedicado | Incluido en planes $299+ |

---

## Modelo Freemium Detallado

```
┌─────────────────────────────────────────────────────────────────┐
│                         FREE TIER                                │
│  ✓ Análisis ilimitado de pronunciación                         │
│  ✓ Tutorial IPA completo                                        │
│  ✓ Drills básicos (todos los sonidos)                          │
│  ✓ 1 idioma activo                                              │
│  ✓ Historial 7 días                                             │
│  ✗ Sin métricas de grupo                                        │
│  ✗ Sin API                                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TEAM PLAN - $99/mes                          │
│  ✓ Todo lo gratuito                                             │
│  ✓ Hasta 50 usuarios                                            │
│  ✓ Dashboard de grupo básico                                    │
│  ✓ Reportes mensuales                                           │
│  ✓ Idiomas ilimitados                                           │
│  ✓ Historial 90 días                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BUSINESS PLAN - $299/mes                       │
│  ✓ Todo en Team                                                 │
│  ✓ Usuarios ilimitados                                          │
│  ✓ Contenido personalizado                                      │
│  ✓ API básica (10k requests/mes)                                │
│  ✓ Historial ilimitado                                          │
│  ✓ Soporte prioritario                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ENTERPRISE - Custom pricing                     │
│  ✓ Todo en Business                                             │
│  ✓ White-label                                                  │
│  ✓ SSO/SAML                                                     │
│  ✓ API ilimitada                                                │
│  ✓ On-premise opcional                                          │
│  ✓ SLA garantizado                                              │
│  ✓ Onboarding dedicado                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estrategia Open Source

### Código Abierto (MIT/Apache 2.0)
- `ipa_core/` - Motor de análisis fonético
- `plugins/` - Backends ASR, TTS, comparadores
- `data/ipa_catalog/` - Catálogos de sonidos por idioma
- `pronunciapa_client/` - App Flutter
- Documentación y ejemplos

### Código Propietario (Backend B2B)
- Sistema de métricas/analytics grupales
- Dashboard administrativo
- Billing/subscriptions
- White-label customization engine
- API gateway con rate limiting

### Beneficios del Open Source
1. **Comunidad** - Contribuciones de idiomas/acentos regionales
2. **Confianza** - Transparencia en cómo funciona el análisis
3. **Adopción** - Desarrolladores pueden extender/integrar
4. **Calidad** - Bug reports y PRs de la comunidad
5. **Marketing** - Visibilidad orgánica en GitHub

---

## Diferenciadores vs Competencia

| Aspecto | ELSA Speak | Duolingo | PronunciaPA |
|---------|------------|----------|-------------|
| Foco | Solo pronunciación | General (poco foco) | **Solo pronunciación** |
| IPA visible | ❌ Interno | ❌ No usa | ✅ **Enseña IPA** |
| Idiomas | Inglés only | Muchos | **Extensible** |
| Open source | ❌ | ❌ | ✅ |
| Offline | Parcial | ❌ | ✅ Full |
| B2B tools | Limitado | ❌ | ✅ Diseñado para |
| Precio B2C | $12/mes | $7/mes | **Gratis** |
| Personalizable | ❌ | ❌ | ✅ Plugins |

---

## Roadmap de Monetización

### Fase 1: Foundation (Q1 2026) ← **Estamos aquí**
- [x] Motor IPA core funcional
- [x] App básica con análisis
- [x] Tutorial IPA interactivo
- [ ] Landing page + waitlist

### Fase 2: Growth (Q2 2026)
- [ ] Beta pública gratuita
- [ ] 1000 usuarios individuales
- [ ] Primer idioma completo (inglés 44 fonemas)
- [ ] Segundo idioma (español)

### Fase 3: Monetization (Q3 2026)
- [ ] Team Plan launch
- [ ] 10 clientes B2B piloto
- [ ] Dashboard básico de grupo
- [ ] API documentada

### Fase 4: Scale (Q4 2026)
- [ ] Business Plan
- [ ] Integración LMS
- [ ] 5 idiomas
- [ ] Mobile app stores

---

## Métricas Clave (KPIs)

### Usuarios
- MAU (Monthly Active Users)
- DAU/MAU ratio (engagement)
- Retención D1, D7, D30

### Negocio
- MRR (Monthly Recurring Revenue)
- Conversion rate free→paid
- Churn rate B2B
- LTV (Lifetime Value) por plan

### Producto
- Sonidos practicados/usuario/día
- Completion rate tutoriales
- NPS (Net Promoter Score)

---

## Próximos Pasos Técnicos

### Inmediato (Esta semana)
1. ✅ Fix errores Python 3.9
2. ⏳ Progress tracking (persistir avance usuario)
3. ⏳ Más sonidos en `en_learning.yaml`

### Corto plazo (Este mes)
4. [ ] Spanish learning content (`es_learning.yaml`)
5. [ ] Landing page con waitlist
6. [ ] CI/CD pipeline
7. [ ] Tests automatizados

### Medio plazo (2-3 meses)
8. [ ] User accounts (auth)
9. [ ] Cloud backend (sync progreso)
10. [ ] B2B dashboard MVP
11. [ ] Play Store / App Store

---

## Contacto y Recursos

- **Repo**: https://github.com/[tu-usuario]/PronunciaPA
- **Docs**: `/docs/` en el repo
- **Backlog**: `docs/backlog.md`
- **Tech Stack**: `conductor/tech-stack.md`
