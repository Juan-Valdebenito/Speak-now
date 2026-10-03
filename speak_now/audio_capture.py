"""Captura de audio: del micrófono o del sonido que reproduce el PC.

Hay dos fuentes y las dos entregan lo mismo (bloques float32 mono a 16 kHz):

- AudioCapture: un micrófono (con sounddevice).
- SystemAudioCapture: lo que suena por los parlantes, como videos o llamadas
  (WASAPI loopback, solo en Windows, con PyAudioWPatch).

Usa create_capture() para crear la que corresponda.
"""

import queue
import sys

import numpy as np
import sounddevice as sd

from speak_now import config

# Fuentes de audio posibles.
SOURCE_MIC = "mic"
SOURCE_SYSTEM = "system"

try:
    if sys.platform != "win32":
        raise ImportError("WASAPI loopback solo existe en Windows")
    import pyaudiowpatch as pyaudio
    SYSTEM_AUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    SYSTEM_AUDIO_AVAILABLE = False


def list_input_devices():
    """Devuelve [(índice, nombre), ...] de los dispositivos con entrada de audio."""
    return [
        (i, dev["name"])
        for i, dev in enumerate(sd.query_devices())
        if dev["max_input_channels"] > 0
    ]


def list_loopback_devices():
    """Devuelve [(índice, nombre), ...] de las salidas de audio que se pueden grabar.

    Los índices son de PyAudioWPatch (no coinciden con los de sounddevice).
    """
    if not SYSTEM_AUDIO_AVAILABLE:
        return []
    p = pyaudio.PyAudio()
    try:
        return [(dev["index"], dev["name"])
                for dev in p.get_loopback_device_info_generator()]
    finally:
        p.terminate()


def create_capture(source=SOURCE_MIC, device=None):
    """Crea la captura para `source` ("mic" o "system")."""
    if source == SOURCE_SYSTEM:
        return SystemAudioCapture(device=device)
    return AudioCapture(device=device)


class _BaseCapture:
    """Lógica común: cola de bloques, fragmentos y corte de frases por silencio.

    Las subclases implementan start() y stop(), y meten en la cola bloques
    float32 mono de `block_size` muestras a `sample_rate`.
    """

    def __init__(self, device=None, sample_rate=config.SAMPLE_RATE,
                 block_duration=config.BLOCK_DURATION):
        self.device = device
        self.sample_rate = sample_rate
        self.block_size = int(sample_rate * block_duration)
        self._queue = queue.Queue()

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def read_block(self, timeout=None):
        """Devuelve el siguiente bloque pequeño (BLOCK_DURATION segundos)."""
        return self._queue.get(timeout=timeout)

    def drain_blocks(self):
        """Saca y devuelve todos los bloques que hay en la cola, sin esperar."""
        blocks = []
        try:
            while True:
                blocks.append(self._queue.get_nowait())
        except queue.Empty:
            return blocks

    def chunks(self, duration=config.CHUNK_DURATION):
        """Generador infinito de fragmentos de `duration` segundos."""
        target = int(self.sample_rate * duration)
        buffer = []
        size = 0
        while True:
            block = self.read_block()
            buffer.append(block)
            size += len(block)
            if size >= target:
                yield np.concatenate(buffer)
                buffer, size = [], 0

    def phrases(self, silence_threshold=config.SILENCE_THRESHOLD,
                silence_duration=config.SILENCE_DURATION,
                max_duration=config.MAX_PHRASE_DURATION,
                min_duration=config.MIN_PHRASE_DURATION,
                stop_event=None):
        """Generador de frases: corta el audio cuando detecta silencio.

        Así cada fragmento contiene frases completas en vez de cortes
        arbitrarios, lo que mejora mucho la transcripción.
        Si se pasa `stop_event` (threading.Event), termina cuando se activa.
        """
        block_seconds = self.block_size / self.sample_rate
        silent_blocks_needed = round(silence_duration / block_seconds)
        max_blocks = round(max_duration / block_seconds)
        min_samples = int(min_duration * self.sample_rate)

        buffer = []
        silent_blocks = 0
        speaking = False
        while stop_event is None or not stop_event.is_set():
            try:
                block = self.read_block(timeout=0.5)
            except queue.Empty:
                # El sonido del PC deja de mandar bloques cuando nada se
                # reproduce (ej. se pausa el video): eso también es silencio.
                if speaking:
                    speaking = False
                    audio = np.concatenate(buffer)
                    buffer = []
                    if len(audio) >= min_samples:
                        yield audio
                continue
            is_speech = rms_level(block) >= silence_threshold

            if not speaking:
                if is_speech:
                    speaking = True
                    buffer = [block]
                    silent_blocks = 0
                continue

            buffer.append(block)
            silent_blocks = 0 if is_speech else silent_blocks + 1

            if silent_blocks >= silent_blocks_needed or len(buffer) >= max_blocks:
                audio = np.concatenate(buffer)
                speaking = False
                buffer = []
                if len(audio) >= min_samples:
                    yield audio


class AudioCapture(_BaseCapture):
    """Graba del micrófono en segundo plano y entrega bloques de audio por una cola.

    Uso:
        with AudioCapture() as mic:
            for chunk in mic.chunks():
                ...  # chunk es un np.ndarray float32 mono a 16 kHz
    """

    def __init__(self, device=None, sample_rate=config.SAMPLE_RATE,
                 block_duration=config.BLOCK_DURATION):
        super().__init__(device, sample_rate, block_duration)
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        # Se ejecuta en un hilo de sounddevice: solo copiamos y encolamos.
        if status:
            print(f"[audio] {status}")
        self._queue.put(indata[:, 0].copy())

    def start(self):
        self._stream = sd.InputStream(
            device=self.device,
            channels=config.CHANNELS,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class SystemAudioCapture(_BaseCapture):
    """Graba lo que suena por los parlantes (videos, llamadas, juegos...).

    Usa WASAPI loopback, así que solo funciona en Windows. `device` es un
    índice de list_loopback_devices(); None = los parlantes predeterminados.
    La salida de audio suele ir a 44.1/48 kHz en estéreo: se convierte a
    16 kHz mono para que el resto del programa no note la diferencia.
    """

    def __init__(self, device=None, sample_rate=config.SAMPLE_RATE,
                 block_duration=config.BLOCK_DURATION):
        if not SYSTEM_AUDIO_AVAILABLE:
            raise RuntimeError("Capturar el sonido del PC solo funciona en Windows "
                               "(falta el paquete PyAudioWPatch)")
        super().__init__(device, sample_rate, block_duration)
        self._block_duration = block_duration
        self._pyaudio = None
        self._stream = None
        self._resampler = None
        self._channels = 0
        self._input_rate = 0
        self._pending = np.zeros(0, dtype=np.float32)

    def start(self):
        # Importamos aquí: PyAV ya viene con faster-whisper y tiene un buen
        # conversor de frecuencia de muestreo.
        import av

        self._pyaudio = pyaudio.PyAudio()
        try:
            if self.device is None:
                info = self._pyaudio.get_default_wasapi_loopback()
            else:
                info = self._pyaudio.get_device_info_by_index(self.device)
        except (OSError, LookupError) as exc:
            self._pyaudio.terminate()
            self._pyaudio = None
            raise RuntimeError("No se encontró la salida de audio para grabar") from exc

        self._channels = int(info["maxInputChannels"])
        self._input_rate = int(info["defaultSampleRate"])
        self._resampler = av.AudioResampler(format="flt", layout="mono",
                                            rate=self.sample_rate)
        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=self._channels,
            rate=self._input_rate,
            input=True,
            input_device_index=info["index"],
            frames_per_buffer=int(self._input_rate * self._block_duration),
            stream_callback=self._callback,
        )
        self._stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        # Se ejecuta en un hilo de PortAudio: convertimos y encolamos.
        import av

        samples = np.frombuffer(in_data, dtype=np.float32)
        layout = "mono" if self._channels == 1 else "stereo"
        if self._channels > 2:
            # El resampler no conoce todos los formatos de canales: nos
            # quedamos con los dos primeros (izquierdo y derecho).
            samples = samples.reshape(-1, self._channels)[:, :2].reshape(-1)
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1),
                                           format="flt", layout=layout)
        frame.sample_rate = self._input_rate
        converted = [f.to_ndarray().reshape(-1)
                     for f in self._resampler.resample(frame)]
        if converted:
            self._pending = np.concatenate([self._pending, *converted])
        # Entregamos bloques del mismo tamaño que el micrófono.
        while len(self._pending) >= self.block_size:
            self._queue.put(self._pending[:self.block_size].copy())
            self._pending = self._pending[self.block_size:]
        return (None, pyaudio.paContinue)

    def stop(self):
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._pyaudio is not None:
            self._pyaudio.terminate()
            self._pyaudio = None


def rms_level(audio):
    """Volumen (RMS) de un bloque de audio, útil para medir si hay voz."""
    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
