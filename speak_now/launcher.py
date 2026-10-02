"""Ventana de inicio: la persona elige la dirección de traducción y el micrófono."""

import json
import tkinter as tk
from dataclasses import asdict, dataclass
from tkinter import ttk

import sounddevice as sd

from speak_now import config
from speak_now.audio_capture import rms_level
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

# Volumen (RMS) que llena el medidor del micrófono.
METER_MAX_LEVEL = 0.2
METER_REFRESH_MS = 60
METER_WIDTH = 200
METER_HEIGHT = 8


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


def _load_last_choices():
    """Opciones de la última vez (o {} si no hay o el archivo está dañado)."""
    try:
        with open(config.USER_SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_choices(settings, device_name):
    # Guardamos el nombre del micrófono además del índice: los índices
    # cambian al conectar o desconectar dispositivos.
    data = asdict(settings) | {"device_name": device_name}
    try:
        with open(config.USER_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # no es grave: la próxima vez se usan los valores por defecto


class _MicMeter:
    """Escucha un micrófono en segundo plano solo para medir el volumen."""

    def __init__(self):
        self.level = 0.0
        self._stream = None

    def start(self, device):
        """Abre el micrófono. Devuelve False si no se pudo."""
        self.stop()
        try:
            self._stream = sd.InputStream(
                device=device, channels=config.CHANNELS,
                samplerate=config.SAMPLE_RATE, dtype="float32",
                blocksize=int(config.SAMPLE_RATE * config.BLOCK_DURATION),
                callback=self._callback,
            )
            self._stream.start()
            return True
        except (sd.PortAudioError, ValueError):
            self._stream = None
            return False

    def _callback(self, indata, frames, time_info, status):
        self.level = rms_level(indata[:, 0])

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = 0.0

    @property
    def running(self):
        return self._stream is not None


def ask_settings():
    """Muestra la ventana de inicio. Devuelve Settings, o None si se cancela."""
    _enable_dpi_awareness()
    root = tk.Tk()
    root.title("Speak-now – Traductor en vivo")
    root.resizable(False, False)
    result = {}
    last = _load_last_choices()
    meter = _MicMeter()

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Speak-now", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Subtítulos traducidos en vivo, sin internet.",
              foreground="#666").pack(anchor="w", pady=(0, 15))

    # Dirección de traducción
    ttk.Label(frame, text="¿Qué idioma vas a escuchar?",
              font=("Segoe UI", 10, "bold")).pack(anchor="w")
    last_direction = next(
        (i for i, (src, dst, _l) in enumerate(DIRECTIONS)
         if (src, dst) == (last.get("from_code"), last.get("to_code"))), 0)
    direction = tk.IntVar(value=last_direction)
    for i, (_src, _dst, label) in enumerate(DIRECTIONS):
        ttk.Radiobutton(frame, text=label, variable=direction, value=i).pack(
            anchor="w", padx=10)

    # Micrófono
    ttk.Label(frame, text="Micrófono", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", pady=(15, 2))
    mics = _microphones()
    mic_labels = [DEFAULT_DEVICE_LABEL] + [name for _i, name in mics]
    mic_box = ttk.Combobox(frame, values=mic_labels, state="readonly", width=50)
    last_mic = last.get("device_name")
    mic_box.current(mic_labels.index(last_mic) if last_mic in mic_labels else 0)
    mic_box.pack(anchor="w", fill="x")

    def selected_device():
        index = mic_box.current()
        return None if index == 0 else mics[index - 1][0]

    # Medidor de volumen: confirma que el micrófono elegido capta la voz.
    meter_row = ttk.Frame(frame)
    meter_row.pack(fill="x", pady=(6, 0))
    meter_bar = tk.Canvas(meter_row, width=METER_WIDTH, height=METER_HEIGHT,
                          bg="#E4E7EC", highlightthickness=0)
    meter_fill = meter_bar.create_rectangle(0, 0, 0, METER_HEIGHT, outline="")
    meter_bar.pack(side="left")
    meter_label = ttk.Label(meter_row, foreground="#666")
    meter_label.pack(side="left", padx=(10, 0))

    def restart_meter(_event=None):
        if not meter.start(selected_device()):
            meter_label.config(text="No se pudo abrir este micrófono",
                               foreground="#D33")

    def refresh_meter():
        if meter.running:
            level = meter.level
            # Raíz cuadrada: así los volúmenes bajos también mueven la barra.
            fraction = min(1.0, level / METER_MAX_LEVEL) ** 0.5
            voice = level >= config.SILENCE_THRESHOLD
            meter_bar.coords(meter_fill, 0, 0, fraction * METER_WIDTH, METER_HEIGHT)
            meter_bar.itemconfig(meter_fill, fill="#3DDC84" if voice else "#A0A7B4")
            if voice:
                meter_label.config(text="● Se detecta voz", foreground="#1E9E5A")
            else:
                meter_label.config(text="Habla para probar el micrófono",
                                   foreground="#666")
        else:
            meter_bar.coords(meter_fill, 0, 0, 0, METER_HEIGHT)
        root.after(METER_REFRESH_MS, refresh_meter)

    mic_box.bind("<<ComboboxSelected>>", restart_meter)

    # Modelo de Whisper
    ttk.Label(frame, text="Modelo de reconocimiento de voz",
              font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 2))
    model_box = ttk.Combobox(frame, values=[label for _m, label in MODELS],
                             state="readonly", width=50)
    model_names = [m for m, _label in MODELS]
    default_model = last.get("model", config.WHISPER_MODEL)
    model_box.current(model_names.index(default_model)
                      if default_model in model_names else 0)
    model_box.pack(anchor="w", fill="x")

    show_original = tk.BooleanVar(
        value=bool(last.get("show_original", config.SHOW_ORIGINAL)))
    ttk.Checkbutton(frame, text="Mostrar también el texto original",
                    variable=show_original).pack(anchor="w", pady=(15, 0))

    def close():
        meter.stop()
        root.destroy()

    def start():
        src, dst, _label = DIRECTIONS[direction.get()]
        settings = Settings(
            from_code=src,
            to_code=dst,
            device=selected_device(),
            model=model_names[model_box.current()],
            show_original=show_original.get(),
        )
        _save_choices(settings, mic_box.get())
        result["settings"] = settings
        close()

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(20, 0))
    ttk.Button(buttons, text="Salir", command=close).pack(side="right")
    start_button = ttk.Button(buttons, text="Iniciar", command=start)
    start_button.pack(side="right", padx=(0, 8))
    start_button.focus_set()
    root.bind("<Return>", lambda _e: start())
    root.bind("<Escape>", lambda _e: close())
    root.protocol("WM_DELETE_WINDOW", close)

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

    restart_meter()
    refresh_meter()
    root.mainloop()
    return result.get("settings")
