"""Prueba de la Parte 1: lista dispositivos y muestra un medidor de volumen.

Ejecutar desde la raíz del proyecto:
    python -m scripts.test_microphone            # micrófono por defecto
    python -m scripts.test_microphone --device 3 # micrófono específico
    python -m scripts.test_microphone --system   # sonido del PC (solo Windows)
"""

import argparse

from speak_now.audio_capture import (SOURCE_MIC, SOURCE_SYSTEM, create_capture,
                                     list_input_devices, list_loopback_devices,
                                     rms_level)


def main():
    parser = argparse.ArgumentParser(description="Prueba de micrófono")
    parser.add_argument("--device", type=int, default=None,
                        help="Índice del dispositivo (ver lista)")
    parser.add_argument("--system", action="store_true",
                        help="Escuchar el sonido del PC en vez del micrófono")
    args = parser.parse_args()

    if args.system:
        print("Salidas de audio que se pueden grabar:")
        for idx, name in list_loopback_devices():
            print(f"  [{idx}] {name}")
        print("
Reproduce un video o música... (Ctrl+C para salir)
")
    else:
        print("Micrófonos disponibles:")
        for idx, name in list_input_devices():
            print(f"  [{idx}] {name}")
        print("
Habla al micrófono... (Ctrl+C para salir)
")

    source = SOURCE_SYSTEM if args.system else SOURCE_MIC
    try:
        with create_capture(source, args.device) as capture:
            while True:
                level = rms_level(capture.read_block())
                bar = "#" * min(int(level * 300), 50)
                print(f"{level:6.3f} |{bar:<50}|", end="", flush=True)
    except KeyboardInterrupt:
        print("
Listo.")


if __name__ == "__main__":
    main()
