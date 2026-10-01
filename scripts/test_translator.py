"""Prueba de la Parte 3: traduce texto escrito o lo que dices al micrófono.

Ejecutar desde la raíz del proyecto:
    python -m scripts.test_translator                      # escribe en inglés -> español
    python -m scripts.test_translator --from es --to en    # español -> inglés
    python -m scripts.test_translator --mic                # habla al micrófono
"""

import argparse
import time

from speak_now import config
from speak_now.translator import Translator


def run_text(translator):
    print("Escribe una frase y presiona Enter (Ctrl+C para salir)\n")
    while True:
        text = input("> ")
        start = time.perf_counter()
        result = translator.translate(text)
        print(f"  {result}   ({time.perf_counter() - start:.2f}s)")


def run_mic(translator, args):
    # Importamos aquí para que el modo texto no tenga que cargar Whisper.
    from speak_now.audio_capture import AudioCapture
    from speak_now.transcriber import Transcriber

    print(f"Cargando modelo '{args.model}'...")
    transcriber = Transcriber(model_size=args.model)
    print("Listo. Habla al micrófono... (Ctrl+C para salir)\n")
    with AudioCapture(device=args.device) as mic:
        for phrase in mic.phrases():
            text = transcriber.transcribe(phrase, language=args.from_code)
            if text:
                print(f"[{args.from_code}] {text}")
                print(f"[{args.to_code}] {translator.translate(text)}\n")


def main():
    parser = argparse.ArgumentParser(description="Prueba de traducción")
    parser.add_argument("--from", dest="from_code", default="en",
                        choices=list(config.LANGUAGES))
    parser.add_argument("--to", dest="to_code", default="es",
                        choices=list(config.LANGUAGES))
    parser.add_argument("--mic", action="store_true",
                        help="Traducir lo que se dice al micrófono")
    parser.add_argument("--model", default=config.WHISPER_MODEL,
                        help="Modelo de Whisper (solo con --mic)")
    parser.add_argument("--device", type=int, default=None,
                        help="Índice del micrófono (solo con --mic)")
    args = parser.parse_args()

    if args.from_code == args.to_code:
        parser.error("--from y --to deben ser idiomas distintos")

    translator = Translator(args.from_code, args.to_code)
    try:
        if args.mic:
            run_mic(translator, args)
        else:
            run_text(translator)
    except (KeyboardInterrupt, EOFError):
        print("\nListo.")


if __name__ == "__main__":
    main()
