"""Ventana de inicio: la persona elige la dirección de traducción y el micrófono."""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import sounddevice as sd

from speak_now import config
from speak_now.subtitle_window import _enable_dpi_awareness

DIRECTIONS = [
    ("en", "es", "Inglés → Español"),
    ("es", "en", "Español → Inglés"),
]

MODELS = [
    ("tiny", "tiny – muy rápido, menos preciso"),
    ("base", "base – rápido"),
    ("small", "small – equilibrado (recomendado)"),
    ("medium", "medium – preciso, lento sin GPU"),
]

DEFAULT_DEVICE_LABEL = "Predeterminado del sistema"


@dataclass
class Settings:
    from_code: str = "en"
    to_code: str = "es"
    device: int | None = None
    model: str = config.WHISPER_MODEL
    show_original: bool = config.SHOW_ORIGINAL


def _microphones():
    """Micrófonos de la misma API de audio que el predeterminado.

    Windows repite cada micrófono una vez por API (MME, DirectSound, WASAPI...);
    filtrando por la API del predeterminado la lista queda sin duplicados.
    """
    try:
        default_api = sd.query_devices(kind="input")["hostapi"]
    except (sd.PortAudioError, ValueError):
        default_api = None
    return [
        (i, dev["name"])
        for i, dev in enumerate(sd.query_devices())
        if dev["max_input_channels"] > 0
        and (default_api is None or dev["hostapi"] == default_api)
    ]


def ask_settings():
    """Muestra la ventana de inicio. Devuelve Settings, o None si se cancela."""
    _enable_dpi_awareness()
    root = tk.Tk()
    root.title("Speak-now – Traductor en vivo")
    root.resizable(False, False)
    result = {}

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Speak-now", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Subtítulos traducidos en vivo, sin internet.",
              foreground="#666").pack(anchor="w", pady=(0, 15))

    # Dirección de traducción
    ttk.Label(frame, text="¿Qué idioma vas a escuchar?",
              font=("Segoe UI", 10, "bold")).pack(anchor="w")
    direction = tk.IntVar(value=0)
    for i, (_src, _dst, label) in enumerate(DIRECTIONS):
        ttk.Radiobutton(frame, text=label, variable=direction, value=i).pack(
            anchor="w", padx=10)

    # Micrófono
    ttk.Label(frame, text="Micrófono", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", pady=(15, 2))
    mics = _microphones()
    mic_labels = [DEFAULT_DEVICE_LABEL] + [name for _i, name in mics]
    mic_box = ttk.Combobox(frame, values=mic_labels, state="readonly", width=50)
    mic_box.current(0)
    mic_box.pack(anchor="w", fill="x")

    # Modelo de Whisper
    ttk.Label(frame, text="Modelo de reconocimiento de voz",
              font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 2))
    model_box = ttk.Combobox(frame, values=[label for _m, label in MODELS],
                             state="readonly", width=50)
    model_names = [m for m, _label in MODELS]
    model_box.current(model_names.index(config.WHISPER_MODEL)
                      if config.WHISPER_MODEL in model_names else 0)
    model_box.pack(anchor="w", fill="x")

    show_original = tk.BooleanVar(value=config.SHOW_ORIGINAL)
    ttk.Checkbutton(frame, text="Mostrar también el texto original",
                    variable=show_original).pack(anchor="w", pady=(15, 0))

    def start():
        src, dst, _label = DIRECTIONS[direction.get()]
        mic_index = mic_box.current()
        result["settings"] = Settings(
            from_code=src,
            to_code=dst,
            device=None if mic_index == 0 else mics[mic_index - 1][0],
            model=model_names[model_box.current()],
            show_original=show_original.get(),
        )
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(20, 0))
    ttk.Button(buttons, text="Salir", command=root.destroy).pack(side="right")
    start_button = ttk.Button(buttons, text="Iniciar", command=start)
    start_button.pack(side="right", padx=(0, 8))
    start_button.focus_set()
    root.bind("<Return>", lambda _e: start())
    root.bind("<Escape>", lambda _e: root.destroy())

    # Centrar en pantalla
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}"
                  f"+{(root.winfo_screenheight() - h) // 3}")

    # Traer al frente: al abrir desde la terminal puede quedar detrás.
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()

    root.mainloop()
    return result.get("settings")
