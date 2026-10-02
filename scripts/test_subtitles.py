"""Prueba de la Parte 4: muestra subtítulos de ejemplo en la ventana.

Ejecutar desde la raíz del proyecto:
    python -m scripts.test_subtitles

Arrastra la ventana con el mouse. Haz clic en ella y prueba Espacio (pausa),
+ / - (tamaño) y O (texto original). Cierra con Esc o doble clic derecho.
"""

import argparse
import threading
import time

from speak_now.subtitle_window import SubtitleWindow

SAMPLES = [
    ("Hello, my name is John.", "Hola, me llamo John."),
    ("Today we are testing a live translation program.",
     "Hoy estamos probando un programa de traducción en vivo."),
    ("This is a much longer sentence to check that the subtitle wraps "
     "correctly onto several lines when someone talks for a long time "
     "without stopping.",
     "Esta es una frase mucho más larga para comprobar que el subtítulo se "
     "divide correctamente en varias líneas cuando alguien habla durante "
     "mucho tiempo sin parar."),
    ("Where is the nearest train station?",
     "¿Dónde está la estación de tren más cercana?"),
]


def feed(window, stop, delay, close_when_done):
    """Simula el traductor: manda frases desde otro hilo."""
    window.set_state("listening", "Escuchando...")
    time.sleep(1)
    for original, translation in SAMPLES:
        if stop.is_set():
            return
        window.show(translation, original)
        time.sleep(delay)
    if close_when_done:
        window.request_close()


def main():
    parser = argparse.ArgumentParser(description="Prueba de subtítulos")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Segundos entre cada subtítulo")
    parser.add_argument("--close", action="store_true",
                        help="Cerrar la ventana al terminar los ejemplos")
    args = parser.parse_args()

    stop = threading.Event()
    window = SubtitleWindow(on_close=stop.set)
    threading.Thread(target=feed, args=(window, stop, args.delay, args.close),
                     daemon=True).start()
    window.run()


if __name__ == "__main__":
    main()
