"""Configuración central del proyecto."""

# Whisper trabaja a 16 kHz, mono. Capturamos directamente en ese formato
# para no tener que re-muestrear.
SAMPLE_RATE = 16000
CHANNELS = 1

# Tamaño de cada bloque que entrega el micrófono (en segundos).
BLOCK_DURATION = 0.1

# Duración de cada fragmento que se enviará a transcribir (en segundos).
CHUNK_DURATION = 3.0
