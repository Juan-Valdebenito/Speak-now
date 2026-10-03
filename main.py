



import argparse

from speak_now import config
from speak_now.audio_capture import SOURCE_MIC, SOURCE_SYSTEM
from speak_now.launcher import Settings, ask_settings


def parse_args():
    parser = argparse.ArgumentParser(
        description="Traductor de voz con subtítulos en vivo")
    parser.add_argument("--from", dest="from_code", choices=list(config.LANGUAGES),
                        help="Idioma que se escucha (si se indica, no se muestra "
                             "la ventana de inicio)")
    parser.add_argument("--to", dest="to_code", choices=list(config.LANGUAGES),
                        help="Idioma de los subtítulos")
    parser.add_argument("--model", default=config.WHISPER_MODEL,
                        help="Modelo de Whisper: tiny, base, small, medium...")
    parser.add_argument("--source", choices=[SOURCE_MIC, SOURCE_SYSTEM],
                        default=SOURCE_MIC,
                        help="De dónde escuchar: 'mic' (micrófono) o 'system' "
                             "(el sonido del PC: videos, llamadas...; solo Windows)")
    parser.add_argument("--device", type=int, default=None,
                        help="Índice del micrófono o de la salida de audio "
                             "(ver scripts.test_microphone)")
    parser.add_argument("--no-original", action="store_true",
                        help="No mostrar el texto original sobre la traducción")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.from_code:
        to_code = args.to_code or next(c for c in config.LANGUAGES
                                       if c != args.from_code)
        if to_code == args.from_code:
            raise SystemExit("--from y --to deben ser idiomas distintos")
        settings = Settings(
            from_code=args.from_code,
            to_code=to_code,
            source=args.source,
            device=args.device,
            model=args.model,
            show_original=not args.no_original,
        )
    else:
        settings = ask_settings()
        if settings is None:
            return

    # Importamos aquí para que la ventana de inicio abra al instante,
    # sin esperar a que carguen Whisper y Argos.
    from speak_now import app
    app.run(settings)


if __name__ == "__main__":
    main()
