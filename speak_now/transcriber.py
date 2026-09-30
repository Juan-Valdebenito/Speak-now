"""Transcripción de voz a texto usando faster-whisper."""

from faster_whisper import WhisperModel

from speak_now import config


class Transcriber:
    """Convierte audio (np.ndarray float32, mono, 16 kHz) en texto.

    Uso:
        t = Transcriber()
        texto = t.transcribe(audio, language="en")
    """

    def __init__(self, model_size=config.WHISPER_MODEL,
                 device=config.WHISPER_DEVICE,
                 compute_type=config.WHISPER_COMPUTE_TYPE,
                 beam_size=config.WHISPER_BEAM_SIZE):
        # La primera vez descarga el modelo a la carpeta models/.
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=config.MODELS_DIR,
        )
        self.beam_size = beam_size

    def transcribe(self, audio, language=None):
        """Devuelve el texto reconocido.

        `language` es "en", "es" o None (detección automática).
        `audio` puede ser un np.ndarray o la ruta a un archivo de audio.
        """
        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=self.beam_size,
            # Filtro de voz (Silero VAD): ignora silencios y ruido de fondo.
            vad_filter=True,
            # Cada frase se procesa por separado: evita que Whisper
            # "arrastre" texto de frases anteriores.
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
