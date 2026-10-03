# Speak-now

Traductor de voz con subtítulos en vivo, **gratuito y 100 % local**.
Escucha a alguien hablar en inglés y muestra la traducción al español
(o al revés, según elijas) como subtítulos en la parte de abajo de la pantalla.

Todo funciona en tu computador: después de la primera descarga de modelos
no necesita internet ni cuentas de ningún servicio.

## Cómo funciona

```
Micrófono ───► sounddevice ───┐
                               ├─► faster-whisper ──► Argos Translate ──► Tkinter
Sonido del PC ► PyAudioWPatch ─┘   (voz → texto)      (EN ↔ ES)          (subtítulos)
                (solo Windows)
```

1. **sounddevice** graba el micrófono, o **PyAudioWPatch** graba lo que
   suena por los parlantes (videos, llamadas, juegos; solo en Windows).
   El audio se corta en frases cada vez que se detecta un silencio.
2. **faster-whisper** convierte cada frase en texto.
3. **Argos Translate** traduce el texto sin conexión.
4. **Tkinter** muestra la traducción en una barra semitransparente
   siempre visible abajo de la pantalla.

## Requisitos

- Windows, macOS o Linux
- Python 3.10 o superior (en Windows: `py -3.12`)
- ~2 GB de espacio libre (librerías + modelos)

## Instalación

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate          # en macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

Se abre una ventana donde eliges:

- **Qué idioma vas a escuchar:** Inglés → Español o Español → Inglés.
- **Escuchar desde** (solo en Windows): el **micrófono** o el **sonido del PC**.
  Con "Sonido del PC" se traduce lo que suena en tus parlantes o audífonos:
  un video de YouTube, una llamada de Zoom/Meet/Teams, un juego, etc.
- **Micrófono / salida de audio.** Debajo hay un medidor de volumen: habla
  (o reproduce un video) y verás "● Se detecta sonido" si llega audio.
- **Modelo de reconocimiento de voz:** `small` es el recomendado; usa
  `base` o `tiny` si los subtítulos llegan con mucho retraso.
- **Mostrar también el texto original.**

Al presionar **Iniciar** aparece la barra de subtítulos. La primera vez
se descargan los modelos (~480 MB de Whisper `small` y ~100 MB por cada
dirección de traducción), así que puede tardar unos minutos.

**Controles de la barra de subtítulos:**

- Arrastrar con el mouse para moverla.
- `Espacio`: pausar / reanudar.
- `+` / `-`: agrandar / achicar la letra.
- `O`: mostrar / ocultar el texto original.
- Doble clic derecho (o `Esc`) para cerrar.

Los atajos de teclado funcionan después de hacer clic en la barra.
El punto de color de la esquina indica el estado: azul = cargando,
verde = escuchando, amarillo = procesando una frase, gris = en pausa,
rojo = error.

Las opciones elegidas se recuerdan para la próxima vez
(en `user_settings.json`).

### Iniciar directo, sin la ventana de opciones

```bash
python main.py --from en --to es                # inglés → español
python main.py --from es --to en --model base   # español → inglés, modelo rápido
python main.py --from en --device 1 --no-original
python main.py --from en --source system        # traduce el sonido del PC
```

`python main.py --help` muestra todas las opciones.

## Configuración

Todos los ajustes están en [`speak_now/config.py`](speak_now/config.py):

| Ajuste | Qué hace |
|---|---|
| `SILENCE_THRESHOLD` | Volumen mínimo para considerar que hay voz. Bájalo si no detecta tu voz; súbelo si capta ruido. |
| `SILENCE_DURATION` | Silencio necesario para cerrar una frase. |
| `MAX_PHRASE_DURATION` | Largo máximo de una frase si la persona no hace pausas. |
| `WHISPER_MODEL` | Modelo por defecto (`tiny`, `base`, `small`, `medium`, `large-v3`). |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | `"cuda"` / `"float16"` si tienes GPU NVIDIA. |
| `WHISPER_BEAM_SIZE` | `1` = más rápido, `5` = algo más preciso. |
| `SUBTITLE_*` | Tamaño de letra, opacidad, ancho, posición y duración de los subtítulos. |

## Estructura del proyecto

```
main.py                       Punto de entrada
speak_now/
  config.py                   Ajustes
  audio_capture.py            Micrófono / sonido del PC y corte de frases
  transcriber.py              Voz → texto (faster-whisper)
  translator.py               Traducción (Argos Translate)
  subtitle_window.py          Barra de subtítulos (Tkinter)
  launcher.py                 Ventana de opciones al iniciar
  app.py                      Une todas las piezas
scripts/                      Pruebas de cada parte por separado
models/                       Modelos descargados (no se suben a git)
```

## Probar cada parte por separado

```bash
python -m scripts.test_microphone          # medidor de volumen del micrófono
python -m scripts.test_microphone --system # medidor del sonido del PC
python -m scripts.test_transcriber         # voz → texto
python -m scripts.test_translator --mic    # voz → texto → traducción
python -m scripts.test_subtitles           # barra de subtítulos con ejemplos
```

## Problemas comunes

- **Los subtítulos llegan tarde:** usa un modelo más chico (`base` o `tiny`).
- **No detecta mi voz:** revisa el micrófono con `scripts.test_microphone`
  y baja `SILENCE_THRESHOLD`.
- **Aparecen frases que nadie dijo ("Thank you", "Gracias"):** son
  alucinaciones típicas de Whisper con ruido de fondo. Las más comunes se
  filtran en `speak_now/transcriber.py` (`HALLUCINATIONS`).
- **Con "Sonido del PC" no aparece nada:** revisa que el audio salga por la
  salida elegida (por ejemplo, audífonos vs. parlantes) con
  `python -m scripts.test_microphone --system`. Con música de fondo la frase
  puede tardar en cortarse (se corta sola a los `MAX_PHRASE_DURATION` segundos).
- **`python` abre Python 2.7:** activa el entorno virtual (`.venv\Scripts\activate`)
  o usa `py -3.12`.

## Progreso

- [x] Parte 1 – Estructura del proyecto y captura de audio
- [x] Parte 2 – Transcripción con faster-whisper
- [x] Parte 3 – Traducción con Argos Translate
- [x] Parte 4 – Ventana de subtítulos con Tkinter
- [x] Parte 5 – Integración final y selector de idioma
