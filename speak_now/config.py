"""Configuración central del proyecto."""

# Whisper trabaja a 16 kHz, mono. Capturamos directamente en ese formato
# para no tener que re-muestrear.
SAMPLE_RATE = 16000
CHANNELS = 1

# Tamaño de cada bloque que entrega el micrófono (en segundos).
BLOCK_DURATION = 0.1

# Duración de cada fragmento que se enviará a transcribir (en segundos).
CHUNK_DURATION = 3.0

# --- Detección de frases (corte por silencio) ---
# Volumen (RMS) por debajo del cual consideramos que hay silencio.
SILENCE_THRESHOLD = 0.01
# Silencio necesario para dar por terminada una frase (en segundos).
SILENCE_DURATION = 0.6
# Largo máximo de una frase: si alguien habla sin parar, cortamos igual.
MAX_PHRASE_DURATION = 8.0
# Frases más cortas que esto se descartan (clics, golpes, ruido).
MIN_PHRASE_DURATION = 0.4

# --- Transcripción (faster-whisper) ---
# Modelos: "tiny", "base", "small", "medium", "large-v3".
# Más grande = más preciso pero más lento. "small" es buen equilibrio en CPU.
WHISPER_MODEL = "small"
# "cpu" o "cuda" (si tienes GPU NVIDIA con CUDA).
WHISPER_DEVICE = "cpu"
# "int8" es rápido en CPU; con GPU usar "float16".
WHISPER_COMPUTE_TYPE = "int8"
# 1 = más rápido (ideal para tiempo real); 5 = algo más preciso.
WHISPER_BEAM_SIZE = 1
# Carpeta donde se descargan los modelos (ignorada por git).
MODELS_DIR = "models"
