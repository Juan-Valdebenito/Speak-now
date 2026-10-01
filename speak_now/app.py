"""Une todas las piezas: micrófono -> Whisper -> Argos -> subtítulos."""

import threading
import traceback

from speak_now import config
from speak_now.audio_capture import AudioCapture
from speak_now.subtitle_window import SubtitleWindow
from speak_now.transcriber import Transcriber
from speak_now.translator import Translator


def _pipeline(window, settings, stop):
    """Corre en un hilo aparte para no congelar la ventana."""
    try:
        window.set_status(f"Cargando modelo de voz '{settings.model}'... "
                          "(la primera vez se descarga)")
        transcriber = Transcriber(model_size=settings.model)

        window.set_status("Cargando traductor... (la primera vez se descarga)")
        translator = Translator(settings.from_code, settings.to_code)

        src = config.LANGUAGES[settings.from_code]
        dst = config.LANGUAGES[settings.to_code]
        window.set_status(f"Escuchando {src} → {dst}...   "
                          "(arrastra para mover · doble clic derecho para cerrar)")
        print(f"Listo. Escuchando {src} -> {dst}. Cierra la ventana para salir.")

        with AudioCapture(device=settings.device) as mic:
            for phrase in mic.phrases(stop_event=stop):
                text = transcriber.transcribe(phrase, language=settings.from_code)
                if not text or stop.is_set():
                    continue
                translation = translator.translate(text)
                print(f"[{settings.from_code}] {text}\n"
                      f"[{settings.to_code}] {translation}\n")
                window.show(translation, text)
    except Exception as exc:  # noqa: BLE001 - mostramos cualquier error en pantalla
        traceback.print_exc()
        window.set_status(f"Error: {exc}")


def run(settings):
    """Abre la ventana de subtítulos y empieza a traducir. Bloquea hasta cerrar."""
    stop = threading.Event()
    window = SubtitleWindow(on_close=stop.set, show_original=settings.show_original)
    worker = threading.Thread(target=_pipeline, args=(window, settings, stop),
                              daemon=True)
    worker.start()
    window.run()
    stop.set()
