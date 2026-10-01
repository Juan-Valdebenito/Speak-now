"""Ventana de subtítulos: barra semitransparente fija abajo de la pantalla."""

import queue
import sys
import tkinter as tk

from speak_now import config

BG_COLOR = "#000000"
TEXT_COLOR = "#FFFFFF"
ORIGINAL_COLOR = "#B0B0B0"
STATUS_COLOR = "#808080"


def _enable_dpi_awareness():
    """En Windows con pantallas escaladas evita que el texto se vea borroso."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class SubtitleWindow:
    """Muestra subtítulos encima de todas las ventanas.

    show() y set_status() se pueden llamar desde cualquier hilo: los mensajes
    pasan por una cola que la ventana revisa periódicamente, porque Tkinter
    solo se puede manipular desde su propio hilo.

    Controles:
        - Arrastrar con el mouse para mover la ventana.
        - Esc o doble clic derecho para cerrar.
    """

    POLL_MS = 50

    def __init__(self, on_close=None):
        _enable_dpi_awareness()
        self._on_close = on_close
        self._messages = queue.Queue()
        self._clear_job = None
        self._drag_offset = None
        self._moved_by_user = False

        self.root = tk.Tk()
        self.root.title("Speak-now")
        self.root.overrideredirect(True)          # sin bordes ni barra de título
        self.root.attributes("-topmost", True)    # siempre encima
        self.root.attributes("-alpha", config.SUBTITLE_OPACITY)
        self.root.configure(bg=BG_COLOR)

        self.width = int(self.root.winfo_screenwidth() * config.SUBTITLE_WIDTH_RATIO)
        wrap = self.width - 40

        self.original_label = tk.Label(
            self.root, text="", fg=ORIGINAL_COLOR, bg=BG_COLOR,
            font=(config.SUBTITLE_FONT, config.ORIGINAL_FONT_SIZE),
            wraplength=wrap, justify="center",
        )
        self.translation_label = tk.Label(
            self.root, text="", fg=TEXT_COLOR, bg=BG_COLOR,
            font=(config.SUBTITLE_FONT, config.SUBTITLE_FONT_SIZE, "bold"),
            wraplength=wrap, justify="center",
        )
        self.status_label = tk.Label(
            self.root, text="", fg=STATUS_COLOR, bg=BG_COLOR,
            font=(config.SUBTITLE_FONT, config.ORIGINAL_FONT_SIZE, "italic"),
        )
        self.status_label.pack(padx=20, pady=10)

        for widget in (self.root, self.original_label,
                       self.translation_label, self.status_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<Double-Button-3>", lambda _e: self.close())
        self.root.bind("<Escape>", lambda _e: self.close())

        self._reposition()
        self.root.after(self.POLL_MS, self._poll)

    # ---- API pública (segura entre hilos) ----

    def show(self, translation, original=""):
        """Muestra un subtítulo nuevo."""
        self._messages.put(("subtitle", translation, original))

    def set_status(self, text):
        """Mensaje que se ve cuando no hay subtítulo (ej. "Escuchando...")."""
        self._messages.put(("status", text, ""))

    def request_close(self):
        """Pide cerrar la ventana desde otro hilo."""
        self._messages.put(("close", "", ""))

    def run(self):
        """Inicia la ventana. Bloquea hasta que se cierra."""
        self.root.mainloop()

    def close(self):
        if self._on_close:
            self._on_close()
        self.root.destroy()

    # ---- Internos ----

    def _poll(self):
        try:
            while True:
                kind, text, original = self._messages.get_nowait()
                if kind == "close":
                    self.close()
                    return
                if kind == "subtitle":
                    self._render_subtitle(text, original)
                else:
                    self.status_label.config(text=text)
                    self._reposition()
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._poll)

    def _render_subtitle(self, translation, original):
        self.status_label.pack_forget()
        self.original_label.pack_forget()
        self.translation_label.pack_forget()

        if config.SHOW_ORIGINAL and original:
            self.original_label.config(text=original)
            self.original_label.pack(padx=20, pady=(10, 0))
        self.translation_label.config(text=translation)
        self.translation_label.pack(padx=20, pady=10)
        self._reposition()

        # Reinicia el temporizador que borra el subtítulo.
        if self._clear_job is not None:
            self.root.after_cancel(self._clear_job)
        self._clear_job = self.root.after(
            int(config.SUBTITLE_TIMEOUT * 1000), self._clear
        )

    def _clear(self):
        self._clear_job = None
        self.original_label.pack_forget()
        self.translation_label.pack_forget()
        self.status_label.pack(padx=20, pady=10)
        self._reposition()

    def _reposition(self):
        """Ajusta el alto al texto y mantiene fijo el borde inferior."""
        self.root.update_idletasks()
        height = self.root.winfo_reqheight()
        if self._moved_by_user:
            x = self.root.winfo_x()
            bottom = self.root.winfo_y() + self.root.winfo_height()
        else:
            x = (self.root.winfo_screenwidth() - self.width) // 2
            bottom = self.root.winfo_screenheight() - config.SUBTITLE_BOTTOM_MARGIN
        self.root.geometry(f"{self.width}x{height}+{x}+{bottom - height}")

    def _start_drag(self, event):
        self._drag_offset = (event.x_root - self.root.winfo_x(),
                             event.y_root - self.root.winfo_y())

    def _drag(self, event):
        if self._drag_offset is None:
            return
        dx, dy = self._drag_offset
        self._moved_by_user = True
        self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
