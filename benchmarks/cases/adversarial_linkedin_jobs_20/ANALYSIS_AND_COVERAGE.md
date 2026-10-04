# Adversarial LinkedIn Jobs — análisis y cobertura del set de 20

## Resumen de los dos payload originales

### Payload 00
- Caso adversarial realista/concentrado: mezcla inglés-español, typos, emojis, alias de ubicación, ambigüedad remoto/híbrido, modalidades contractuales por geografía y bandas salariales en USD/CRC con diferentes periodicidades.
- La señal relevante está relativamente cerca de la superficie: el reto principal es conservar contexto, prioridad y negaciones sin sobreinterpretar keywords o números.
- Trampas destacadas: nice-to-have vs must-have, salary vs bonus/budgets, horario vs horas mencionadas en entrevistas, “main office” vs área metropolitana/remoto LATAM, y seniority aproximado.

### Payload 01
- Stress test extremo/multicapa: además de contradicciones semánticas, incluye pseudo-JSON/YAML/HTML/Markdown/CSV/email, caracteres Unicode confusables, OCR corrupto, entidades HTML/URL encoding, fragmentos de otros jobs, page chrome, SEO, notas internas, Slack, drafts viejos, snippets de ATS y una sección canonical-ish al final.
- Su reto no es solo extracción: exige source attribution, scope resolution, temporalidad, detección de contaminación, contextualización de unidades/monedas y precedencia entre evidencia.
- Contiene múltiples “decoy classes”: salary decoys, experience-number decoys, location decoys, contact/URL decoys, vacancy-count decoys, schedule decoys y role-title decoys.

## Taxonomía de riesgos que conviene evaluar

1. **Boundary detection:** separar contenido real del job de footer/cookies/SEO/related jobs/stale drafts.
2. **Entity anchoring:** anclar title, employer, location y requisition a la vacante correcta cuando aparecen otras vacantes o candidatos.
3. **Context-preserving normalization:** no convertir múltiples bandas salariales o modalidades en un único valor sin jurisdicción/unidad.
4. **Contradiction resolution:** distinguir conflicto real de variantes compatibles (p.ej., remote-eligible + country-restricted).
5. **Negation/scope:** respetar NOT, preferred, bonus, optional, stale, example, unrelated.
6. **Temporal reasoning:** separar posted/updated/close dates de fechas de proyectos, políticas y snippets obsoletos.
7. **Unicode/OCR robustness:** NFC/NFD, espacios especiales, homoglyphs, fullwidth, 0/O, 1/I sin correcciones globales destructivas.
8. **Numeric typing:** salary vs quota/budget/revenue/latency/headcount/ID/years/shift/percentage.
9. **Taxonomy ambiguity:** alias razonables vs títulos realmente distintos.
10. **Cross-field consistency:** description ↔ criteria_list ↔ type/location/modality, sin asumir que el primer campo siempre gana.

## Diseño de los 18 nuevos payloads

- **02 — Senior Frontend Engineer**: Toronto, ON, Canada; remote within Canada; optional Vancouver hub. Comp: CAD 145,000–185,000 base/year for Canada employee; 10% target bonus; equity may apply. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **03 — Senior Data Engineer**: Colombia; Bogotá or Medellín; remote-eligible within Colombia, LATAM contractor exceptions possible. Comp: COP 18,000,000–27,000,000 gross/month for Colombia employee OR USD 4,800–7,000/month contractor depending country. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **04 — Senior Product Manager, Payments**: Mexico City, Mexico; primary office in Polanco; candidates elsewhere in Mexico considered case-by-case. Comp: MXN $110,000–$155,000 gross/month + 15% target bonus + equity eligibility. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **05 — SOC Analyst II**: Madrid, Spain primary; Barcelona secondary; must be resident/authorized in Spain. Comp: EUR €38,000–€52,000 gross/year + shift differential + up to 8% bonus. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **06 — Senior Site Reliability Engineer**: Poland or Czechia; Warsaw/Prague hubs; remote within approved EU/EEA countries. Comp: Poland B2B PLN 28,000–38,000/month + VAT where applicable; employee bands differ; Czech employee CZK 150,000–190,000/month. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **07 — Senior iOS Engineer**: Brazil; São Paulo hub; remote within Brazil. Comp: BRL R$22,000–R$30,000 gross/month CLT + benefits + annual bonus up to 10%. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **08 — Senior Product Designer**: Argentina or Uruguay; Buenos Aires and Montevideo hubs; remote within those countries. Comp: USD $3,800–$5,800/month contractor equivalent; localized payroll bands may be ARS/UYU and indexed periodically. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **09 — Enterprise Account Executive**: Remote Americas with preference Mexico/Colombia/Florida; legal hiring varies by country. Comp: US employee base $110,000–$140,000 + variable for OTE $220,000–$280,000 at 100% quota; LATAM localized bands differ. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **10 — Senior FP&A Analyst**: London primary, Manchester secondary, United Kingdom. Comp: GBP £65,000–£82,000 base/year + 10–15% target bonus. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **11 — Registered Nurse – Emergency Department**: Queens, New York City, NY; primary hospital campus; must hold/obtain NY RN license. Comp: USD $58.50–$74.25/hour base depending experience + night/weekend differentials; union rules may apply. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **12 — Warehouse Operations Manager**: Fort Worth, Texas, USA; DFW fulfillment center. Comp: USD $92,000–$118,000 base/year + 12% target bonus. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **13 — Senior Privacy Counsel**: Dublin, Ireland or London, UK; other approved European locations may be considered. Comp: Ireland €120,000–€155,000 base/year; UK £105,000–£135,000 base/year; bonus/equity eligibility varies. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **14 — Customer Success Manager, APAC**: Singapore preferred; remote in selected APAC markets where employment is supported. Comp: SGD 105,000–135,000 base/year + 15% variable tied to retention/expansion; localized APAC bands differ. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **15 — Senior Backend Engineer – Online Games**: Finland or Sweden; Helsinki primary studio, Stockholm satellite. Comp: Finland €70,000–€92,000/year; Sweden SEK 780,000–980,000/year depending location/level. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **16 — Research Scientist – Computational Biology**: Cambridge, Massachusetts, USA; Boston biotech cluster. Comp: USD $135,000–$175,000 base/year for Research Scientist; Senior Scientist range may be higher and is not guaranteed. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **17 — Senior Growth Marketing Manager**: France; Paris hub; remote within France. Comp: EUR €72,000–€92,000 base/year + 10% bonus. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **18 — Senior Mechanical Design Engineer**: Santa Catarina, Nuevo León, Mexico (Monterrey metro). Comp: MXN $65,000–$90,000 gross/month + 10% performance bonus. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.
- **19 — Senior Technical Recruiter**: Remote in Mexico, Colombia, Costa Rica or US states where employed; recruiter team distributed. Comp: LATAM employee/contract equivalents USD $3,500–$5,500/month depending country; US employee base $95,000–$125,000/year; no placement commission. Cubre contaminación por roles relacionados/obsoletos, decoys numéricos específicos del dominio, Unicode/OCR, pseudo-estructuras y conflictos de modalidad/tipo.

## Validación técnica

- Total payloads: **20**.
- Todos los JSON se parsean correctamente en UTF-8.
- Todos conservan exactamente las claves `title`, `description`, `criteria_list`, `type`, `location`, `modality`.
- Todos tienen 10 elementos en `criteria_list`.

### Tamaño por archivo

- 00: 6,976 chars, 183 líneas, 178 chars no-ASCII, schema_ok=True
- 01: 45,428 chars, 2625 líneas, 3,863 chars no-ASCII, schema_ok=True
- 02: 7,778 chars, 142 líneas, 78 chars no-ASCII, schema_ok=True
- 03: 7,628 chars, 149 líneas, 83 chars no-ASCII, schema_ok=True
- 04: 7,889 chars, 145 líneas, 69 chars no-ASCII, schema_ok=True
- 05: 7,456 chars, 150 líneas, 83 chars no-ASCII, schema_ok=True
- 06: 7,576 chars, 149 líneas, 67 chars no-ASCII, schema_ok=True
- 07: 7,273 chars, 144 líneas, 81 chars no-ASCII, schema_ok=True
- 08: 7,560 chars, 149 líneas, 63 chars no-ASCII, schema_ok=True
- 09: 7,513 chars, 149 líneas, 67 chars no-ASCII, schema_ok=True
- 10: 7,045 chars, 146 líneas, 86 chars no-ASCII, schema_ok=True
- 11: 7,532 chars, 147 líneas, 73 chars no-ASCII, schema_ok=True
- 12: 7,119 chars, 150 líneas, 69 chars no-ASCII, schema_ok=True
- 13: 7,675 chars, 148 líneas, 84 chars no-ASCII, schema_ok=True
- 14: 7,486 chars, 145 líneas, 65 chars no-ASCII, schema_ok=True
- 15: 7,346 chars, 147 líneas, 79 chars no-ASCII, schema_ok=True
- 16: 7,430 chars, 148 líneas, 65 chars no-ASCII, schema_ok=True
- 17: 7,135 chars, 146 líneas, 80 chars no-ASCII, schema_ok=True
- 18: 7,284 chars, 147 líneas, 72 chars no-ASCII, schema_ok=True
- 19: 8,071 chars, 149 líneas, 80 chars no-ASCII, schema_ok=True

## Recomendación de uso en evaluación

- Mantener los payloads originales sin modificar para conservar continuidad con tus pruebas previas.
- Usar el `manifest_adversarial_jobs_20.json` como truth/metadata auxiliar; no dárselo al extractor durante una evaluación ciega.
- Evaluar por atributo y por contexto, no solo exact-match global. Ejemplo: una banda salarial correcta pero sin moneda/periodicidad/jurisdicción debería puntuar como parcialmente incorrecta.
- Registrar errores por clase (boundary, anchoring, negation, numeric typing, stale contamination, Unicode/OCR, contradiction resolution) para saber qué regresión introdujo cada cambio del parser/modelo.
- Para robustez, ejecutar dos modos: raw Unicode y una copia normalizada (NFC) y comparar degradación/recuperación.
