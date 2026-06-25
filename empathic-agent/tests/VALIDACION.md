# Guía de validación — Louie (Tesis)

Documentación para reproducir las **Tablas 5 y 6** y generar la **matriz de confusión**.

## Requisitos

- Servidor activo: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- `.env` con `HUME_API_KEY`, `HUME_CONFIG_ID`, `OPENAI_API_KEY`
- Micrófono para pruebas emocionales E1–E5

---

## Tabla 5 — Validación emocional (Hume EVI)

### Procedimiento

1. Imprime los guiones:
   ```powershell
   .venv\Scripts\python.exe tests\print_emotion_scripts.py
   ```

2. Para **cada escenario** (E1–E5):
   - Abre http://localhost:8000
   - Ingresa el **User ID** indicado (`VALID_E1`, `VALID_E2`, …)
   - **Start Session**
   - Lee el guion en voz alta con la emoción indicada (20–40 segundos)
   - **Stop Session**
   - Espera 5 segundos antes del siguiente escenario

3. Analiza resultados y genera matriz:
   ```powershell
   .venv\Scripts\python.exe tests\analyze_emotions.py
   ```

### Escenarios

| Escenario | Emoción esperada | User ID   | Entrada simulada              |
|-----------|------------------|-----------|-------------------------------|
| E1        | Alegría          | VALID_E1  | Relato de experiencia positiva |
| E2        | Tristeza         | VALID_E2  | Relato de pérdida personal     |
| E3        | Ansiedad         | VALID_E3  | Estrés académico               |
| E4        | Sorpresa         | VALID_E4  | Evento inesperado              |
| E5        | Calma            | VALID_E5  | Conversación cotidiana         |

### Métricas

- **Coincidencia estricta**: emoción detectada = emoción esperada (`joy`, `sadness`, etc.)
- **Coincidencia relajada**: incluye alias semánticos (ej. `enthusiasm` cuenta para `joy`)
- **Fórmula**: `(aciertos / escenarios con datos) × 100`

Salidas:
- `logs/validation/emotion_validation_results.csv`
- `logs/validation/confusion_matrix_emotions.png`

---

## Tabla 6 — Persistencia contextual (Mem0)

### Procedimiento automatizado

Con el servidor corriendo:

```powershell
.venv\Scripts\python.exe tests\run_memory_tests.py
```

### Escenarios evaluados

| Prueba | Información almacenada        | Resultado esperado      |
|--------|-------------------------------|-------------------------|
| M1     | Nombre del usuario            | Recuperación correcta   |
| M2     | Hobby favorito                | Recuperación correcta   |
| M3     | Evento emocional previo       | Recuperación correcta   |
| M4     | Preferencia conversacional    | Recuperación correcta   |
| M5     | Historial emocional           | Recuperación correcta   |

Salida: `logs/validation/memory_validation_YYYYMMDD_HHMMSS.csv`

### Prueba manual (sesiones consecutivas)

1. Sesión 1 — User ID `TEST_MANUAL`: di tu nombre, hobby y preferencias.
2. Cierra sesión. **No** borres memorias.
3. Sesión 2 — mismo User ID: pregunta *"¿Recuerdas mi nombre?"*
4. Verifica: `GET http://localhost:8000/memories/TEST_MANUAL`

---

## Matriz de confusión

- **Con datos reales** (tras E1–E5): generada por `analyze_emotions.py`
- **Plantilla ilustrativa** (documentación): `generate_confusion_matrix_demo.py`

```powershell
.venv\Scripts\python.exe tests\generate_confusion_matrix_demo.py
```

Imagen: `logs/validation/confusion_matrix_emotions.png`

---

## Texto sugerido para la tesis

> Se ejecutaron cinco escenarios de conversación simulada con emociones conocidas (Tabla 5). Para cada escenario se registró la emoción primaria detectada por Hume EVI y se calculó el porcentaje de coincidencia respecto a la emoción objetivo, distinguiendo criterio estricto y relajado. La matriz de confusión resume las confusiones entre categorías esperadas y detectadas.
>
> Para Mem0 (Tabla 6) se almacenó información contextual en cinco pruebas controladas y se verificó su recuperación mediante búsqueda semántica, reportando tasa de acierto por prueba.
