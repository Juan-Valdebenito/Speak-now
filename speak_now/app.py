"""Une todas las piezas: micrófono o sonido del PC -> Whisper -> Argos -> subtítulos."""

import threading
import traceback

from speak_now import config
from speak_now.audio_capture import SOURCE_SYSTEM, create_capture
from speak_now.subtitle_window import SubtitleWindow
from speak_now.transcriber import Transcriber
from speak_now.translator import Translator


def _pipeline(window, settings, stop):
    """Corre en un hilo aparte para no congelar la ventana."""
    try:
        window.set_state("loading", f"Cargando modelo de voz '{settings.model}'... "
                                    "(la primera vez se descarga)")
        transcriber = Transcriber(model_size=settings.model)

        window.set_status("Cargando traductor... (la primera vez se descarga)")
        translator = Translator(settings.from_code, settings.to_code)

        src = config.LANGUAGES[settings.from_code]
        dst = config.LANGUAGES[settings.to_code]
        origin = "del PC" if settings.source == SOURCE_SYSTEM else "del micrófono"
        window.set_state("listening", f"Escuchando {src} {origin} → {dst}...")
        print(f"Listo. Escuchando {src} -> {dst}. Cierra la ventana para salir.")

        with create_capture(settings.source, settings.device) as mic:
            for phrase in mic.phrases(stop_event=stop):
                # En pausa seguimos leyendo el micrófono, pero descartamos el audio.
                if window.paused.is_set():
                    continue
                window.set_state("processing")
                text = transcriber.transcribe(phrase, language=settings.from_code)
                translation = translator.translate(text) if text else ""
                window.set_state("listening")
                if not translation or stop.is_set():
                    continue
                print(f"[{settings.from_code}] {text}\n"
                      f"[{settings.to_code}] {translation}\n")
                window.show(translation, text)
    except Exception as exc:  # noqa: BLE001 - mostramos cualquier error en pantalla
        traceback.print_exc()
        window.set_state("error", f"Error: {exc}")


def run(settings):
    """Abre la ventana de subtítulos y empieza a traducir. Bloquea hasta cerrar."""
    stop = threading.Event()
    window = SubtitleWindow(on_close=stop.set, show_original=settings.show_original)
    worker = threading.Thread(target=_pipeline, args=(window, settings, stop),
                              daemon=True)
    worker.start()
    window.run()
    stop.set()
