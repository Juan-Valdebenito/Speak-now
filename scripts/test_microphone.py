"""Prueba de la Parte 1: lista micrófonos y muestra un medidor de volumen.

Ejecutar desde la raíz del proyecto:
    python -m scripts.test_microphone            # micrófono por defecto
    python -m scripts.test_microphone --device 3 # micrófono específico
"""

import argparse

from speak_now.audio_capture import AudioCapture, list_input_devices, rms_level


def main():
    parser = argparse.ArgumentParser(description="Prueba de micrófono")
    parser.add_argument("--device", type=int, default=None,
                        help="Índice del micrófono (ver lista)")
    args = parser.parse_args()

    print("Micrófonos disponibles:")
    for idx, name in list_input_devices():
        print(f"  [{idx}] {name}")

    print("\nHabla al micrófono... (Ctrl+C para salir)\n")
    try:
        with AudioCapture(device=args.device) as mic:
            while True:
                level = rms_level(mic.read_block())
                bar = "#" * min(int(level * 300), 50)
                print(f"\r{level:6.3f} |{bar:<50}|", end="", flush=True)
    except KeyboardInterrupt:
        print("\nListo.")


if __name__ == "__main__":
    main()
