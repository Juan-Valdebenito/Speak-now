"""Ventana de subtítulos: barra semitransparente fija abajo de la pantalla."""

import queue
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont

from speak_now import config

BG_COLOR = "#111318"
TEXT_COLOR = "#FFFFFF"
ORIGINAL_COLOR = "#A9B0BC"
STATUS_COLOR = "#8A919E"
HINT_COLOR = "#5C6370"
# En Windows este color se vuelve transparente: así logramos esquinas redondeadas.
TRANSPARENT_KEY = "#010203"
CORNER_RADIUS = 18
# La barra se ajusta al texto (hasta SUBTITLE_WIDTH_RATIO de la pantalla),
# pero nunca queda más angosta que esto.
MIN_WIDTH = 360
PAD_X, PAD_Y = 44, 14
DOT_SIZE = 8

# Color del punto indicador según el estado.
STATE_COLORS = {
    "loading": "#4C8DFF",
    "listening": "#3DDC84",
    "processing": "#FFB020",
    "paused": "#8A919E",
    "error": "#FF5252",
}

HINT_TEXT = ("Arrastra para mover  ·  Espacio pausa  ·  + / − tamaño  ·  "
             "O texto original  ·  Esc cerrar")

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 60
FADE_STEPS = 8
FADE_MS = 18


def _enable_dpi_awareness():
    """En Windows con pantallas escaladas evita que el texto se vea borroso."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def _blend(color_a, color_b, t):
    """Mezcla dos colores "#RRGGBB": t=0 devuelve a, t=1 devuelve b."""
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


class SubtitleWindow:
    """Muestra subtítulos encima de todas las ventanas.

    show() y set_state() se pueden llamar desde cualquier hilo: los mensajes
    pasan por una cola que la ventana revisa periódicamente, porque Tkinter
    solo se puede manipular desde su propio hilo.

    Controles:
        - Arrastrar con el mouse para mover la ventana.
        - Espacio: pausar / reanudar (ver `paused`).
        - + / -: cambiar el tamaño de letra.
        - O: mostrar / ocultar el texto original.
        - Esc o doble clic derecho para cerrar.
    """

    POLL_MS = 50

    def __init__(self, on_close=None, show_original=config.SHOW_ORIGINAL):
        _enable_dpi_awareness()
        self._on_close = on_close
        self._show_original = show_original
        self._messages = queue.Queue()
        self._clear_job = None
        self._fade_job = None
        self._drag_offset = None
        self._moved_by_user = False
        self._font_size = config.SUBTITLE_FONT_SIZE

        # Lo que se está mostrando ahora.
        self._translation = ""
        self._original = ""
        self._status = ""
        self._state = "loading"

        # El hilo del traductor revisa este evento para no mostrar nada en pausa.
        self.paused = threading.Event()

        self.root = tk.Tk()
        self.root.title("Speak-now")
        self.root.overrideredirect(True)          # sin bordes ni barra de título
        self.root.attributes("-topmost", True)    # siempre encima
        self.root.attributes("-alpha", config.SUBTITLE_OPACITY)

        self._rounded = sys.platform == "win32"
        canvas_bg = TRANSPARENT_KEY if self._rounded else BG_COLOR
        if self._rounded:
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.root.configure(bg=canvas_bg)

        # Semibold se ve más limpio que la negrita; si la fuente no existe
        # (ej. fuera de Windows) usamos la negrita normal.
        semibold = f"{config.SUBTITLE_FONT} Semibold"
        self._emphasis = ((semibold,) if semibold in tkfont.families(self.root)
                          else (config.SUBTITLE_FONT, "bold"))

        self.max_width = int(self.root.winfo_screenwidth()
                             * config.SUBTITLE_WIDTH_RATIO)
        self.width = self.max_width
        self.canvas = tk.Canvas(self.root, width=self.width, height=60,
                                bg=canvas_bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Double-Button-3>", lambda _e: self.close())
        self.root.bind("<Escape>", lambda _e: self.close())
        self.root.bind("<space>", lambda _e: self.toggle_pause())
        for key in ("<plus>", "<KP_Add>", "<equal>"):
            self.root.bind(key, lambda _e: self._change_font_size(+2))
        for key in ("<minus>", "<KP_Subtract>"):
            self.root.bind(key, lambda _e: self._change_font_size(-2))
        self.root.bind("<o>", lambda _e: self._toggle_original())
        self.root.bind("<O>", lambda _e: self._toggle_original())

        self._redraw(fade=False)
        self.root.after(self.POLL_MS, self._poll)

    # ---- API pública (segura entre hilos) ----

    def show(self, translation, original=""):
        """Muestra un subtítulo nuevo."""
        self._messages.put(("subtitle", translation, original))

    def set_state(self, state, text=None):
        """Cambia el indicador de estado (ver STATE_COLORS).

        Si se pasa `text`, también cambia el mensaje que se ve cuando no hay
        subtítulo (ej. "Escuchando...").
        """
        self._messages.put(("state", state, text))

    def set_status(self, text):
        """Solo cambia el mensaje de estado, sin tocar el indicador."""
        self._messages.put(("state", None, text))

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

    def toggle_pause(self):
        if self.paused.is_set():
            self.paused.clear()
            self._state = "listening"
        else:
            self.paused.set()
            self._state = "paused"
            self._translation = self._original = ""
        self._redraw(fade=False)

    # ---- Internos ----

    def _poll(self):
        try:
            while True:
                kind, a, b = self._messages.get_nowait()
                if kind == "close":
                    self.close()
                    return
                if kind == "subtitle":
                    self._render_subtitle(a, b)
                else:
                    self._set_state(a, b)
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._poll)

    def _set_state(self, state, text):
        if state is not None and not self.paused.is_set():
            self._state = state
        if text is not None:
            self._status = text
        self._redraw(fade=False)

    def _render_subtitle(self, translation, original):
        if self.paused.is_set():
            return
        self._translation, self._original = translation, original
        self._redraw(fade=True)

        # Reinicia el temporizador que borra el subtítulo.
        if self._clear_job is not None:
            self.root.after_cancel(self._clear_job)
        self._clear_job = self.root.after(
            int(config.SUBTITLE_TIMEOUT * 1000), self._clear
        )

    def _clear(self):
        self._clear_job = None
        self._translation = self._original = ""
        self._redraw(fade=False)

    def _change_font_size(self, delta):
        self._font_size = max(MIN_FONT_SIZE,
                              min(MAX_FONT_SIZE, self._font_size + delta))
        self._redraw(fade=False)

    def _toggle_original(self):
        self._show_original = not self._show_original
        self._redraw(fade=False)

    def _redraw(self, fade):
        """Dibuja todo el contenido y ajusta el alto de la ventana."""
        c = self.canvas
        c.delete("all")
        if self._fade_job is not None:
            self.root.after_cancel(self._fade_job)
            self._fade_job = None

        center = self.max_width // 2
        wrap = self.max_width - 2 * PAD_X
        small = max(MIN_FONT_SIZE - 2, round(self._font_size * 0.5))
        y = PAD_Y
        faded = []  # (item, color final) de los textos que aparecen suavemente

        def text(content, color, font):
            nonlocal y
            item = c.create_text(center, y, text=content, anchor="n", fill=color,
                                 font=font, width=wrap, justify="center",
                                 tags="text")
            y = c.bbox(item)[3] + 4
            return item

        if self._translation:
            if self._show_original and self._original:
                item = text(self._original, ORIGINAL_COLOR,
                            (config.SUBTITLE_FONT, small))
                faded.append((item, ORIGINAL_COLOR))
            family, *style = self._emphasis
            item = text(self._translation, TEXT_COLOR,
                        (family, self._font_size, *style))
            faded.append((item, TEXT_COLOR))
        else:
            status = "En pausa  —  Espacio para reanudar" \
                if self._state == "paused" else self._status
            text(status, STATUS_COLOR, (config.SUBTITLE_FONT, small, "italic"))
            text(HINT_TEXT, HINT_COLOR, (config.SUBTITLE_FONT, max(9, small - 4)))

        height = y + PAD_Y - 4

        # La barra mide lo justo para el texto, como los subtítulos de un video.
        left, _top, right, _bottom = c.bbox("text")
        self.width = max(MIN_WIDTH, min(self.max_width, right - left + 2 * PAD_X))
        c.move("text", (self.width - self.max_width) / 2, 0)

        # Fondo (redondeado en Windows) e indicador de estado.
        self._background(height)
        dot = STATE_COLORS.get(self._state, STATUS_COLOR)
        x0 = y0 = PAD_Y + 4
        c.create_oval(x0, y0, x0 + DOT_SIZE, y0 + DOT_SIZE, fill=dot, outline="")

        c.config(width=self.width, height=height)
        self._reposition(height)

        if fade:
            for item, color in faded:
                c.itemconfig(item, fill=BG_COLOR)
            self._fade(faded, 1)

    def _background(self, height):
        c, w, r = self.canvas, self.width, CORNER_RADIUS
        if not self._rounded:
            c.create_rectangle(0, 0, w, height, fill=BG_COLOR, outline="",
                               tags="bg")
        else:
            c.create_rectangle(r, 0, w - r, height, fill=BG_COLOR, outline="",
                               tags="bg")
            c.create_rectangle(0, r, w, height - r, fill=BG_COLOR, outline="",
                               tags="bg")
            for x, y in ((0, 0), (w - 2 * r, 0), (0, height - 2 * r),
                         (w - 2 * r, height - 2 * r)):
                c.create_oval(x, y, x + 2 * r, y + 2 * r, fill=BG_COLOR,
                              outline="", tags="bg")
        c.tag_lower("bg")  # el fondo queda detrás del texto

    def _fade(self, items, step):
        t = step / FADE_STEPS
        for item, color in items:
            self.canvas.itemconfig(item, fill=_blend(BG_COLOR, color, t))
        if step < FADE_STEPS:
            self._fade_job = self.root.after(FADE_MS, self._fade, items, step + 1)
        else:
            self._fade_job = None

    def _reposition(self, height):
        """Ajusta el tamaño al contenido manteniendo fijos el centro y el borde
        inferior (así la barra crece hacia los lados y hacia arriba)."""
        if self._moved_by_user:
            center = self.root.winfo_x() + self.root.winfo_width() // 2
            bottom = self.root.winfo_y() + self.root.winfo_height()
        else:
            center = self.root.winfo_screenwidth() // 2
            bottom = self.root.winfo_screenheight() - config.SUBTITLE_BOTTOM_MARGIN
        x = center - self.width // 2
        self.root.geometry(f"{self.width}x{height}+{x}+{bottom - height}")

    def _start_drag(self, event):
        # Las ventanas sin bordes no reciben el foco solas: lo pedimos al hacer
        # clic para que funcionen los atajos de teclado.
        self.root.focus_force()
        self._drag_offset = (event.x_root - self.root.winfo_x(),
                             event.y_root - self.root.winfo_y())

    def _drag(self, event):
        if self._drag_offset is None:
            return
        dx, dy = self._drag_offset
        self._moved_by_user = True
        self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
