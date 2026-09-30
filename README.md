# Speak-now

Traductor de voz con subtítulos en vivo, **gratuito y 100 % local**.
Escucha a alguien hablar en inglés y muestra la traducción al español
(o al revés, según elijas) como subtítulos en la parte de abajo de la pantalla.

## Tecnologías

- **sounddevice** – captura de audio del micrófono
- **faster-whisper** – reconocimiento de voz (voz → texto)
- **Argos Translate** – traducción offline (inglés ↔ español)
- **Tkinter** – ventana de subtítulos

## Requisitos

- Python 3.10 o superior (en Windows: `py -3.12`)

## Instalación

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Progreso

- [x] Parte 1 – Estructura del proyecto y captura de audio
- [x] Parte 2 – Transcripción con faster-whisper
- [ ] Parte 3 – Traducción con Argos Translate
- [ ] Parte 4 – Ventana de subtítulos con Tkinter
- [ ] Parte 5 – Integración final y selector de idioma

## Probar la captura de audio (Parte 1)

```bash
python -m scripts.test_microphone
```

Deberías ver una barra que se mueve cuando hablas.

## Probar la transcripción (Parte 2)

```bash
python -m scripts.test_transcriber                 # hablas en inglés
python -m scripts.test_transcriber --language es   # hablas en español
python -m scripts.test_transcriber --model base    # modelo más rápido
```

La primera vez se descarga el modelo de Whisper (~480 MB para `small`)
en la carpeta `models/`. Cada frase se muestra así:
`[duración del audio | tiempo en procesarla] texto`.

Si el texto aparece con mucho retraso, usa `--model base` o `--model tiny`.
Si no detecta tu voz, baja `SILENCE_THRESHOLD` en `speak_now/config.py`.
