"""Prueba de la Parte 2: habla al micrófono y ve el texto reconocido.

Ejecutar desde la raíz del proyecto:
    python -m scripts.test_transcriber                 # inglés
    python -m scripts.test_transcriber --language es   # español
    python -m scripts.test_transcriber --model base    # modelo más rápido
    python -m scripts.test_transcriber --file audio.wav
"""

import argparse
import time

from speak_now import config
from speak_now.audio_capture import AudioCapture
from speak_now.transcriber import Transcriber


def main():
    parser = argparse.ArgumentParser(description="Prueba de transcripción")
    parser.add_argument("--language", default="en", choices=["en", "es"],
                        help="Idioma que se habla")
    parser.add_argument("--model", default=config.WHISPER_MODEL,
                        help="Modelo de Whisper (tiny, base, small, medium...)")
    parser.add_argument("--device", type=int, default=None,
                        help="Índice del micrófono")
    parser.add_argument("--file", default=None,
                        help="Transcribir un archivo de audio en vez del micrófono")
    args = parser.parse_args()

    print(f"Cargando modelo '{args.model}' (la primera vez se descarga)...")
    transcriber = Transcriber(model_size=args.model)

    if args.file:
        print(transcriber.transcribe(args.file, language=args.language))
        return

    print("Listo. Habla al micrófono... (Ctrl+C para salir)\n")
    try:
        with AudioCapture(device=args.device) as mic:
            for phrase in mic.phrases():
                start = time.perf_counter()
                text = transcriber.transcribe(phrase, language=args.language)
                elapsed = time.perf_counter() - start
                if text:
                    seconds = len(phrase) / config.SAMPLE_RATE
                    print(f"[{seconds:4.1f}s audio | {elapsed:4.1f}s] {text}")
    except KeyboardInterrupt:
        print("\nListo.")


if __name__ == "__main__":
    main()
