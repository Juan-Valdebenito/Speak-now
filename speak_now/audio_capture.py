"""Captura de audio del micrófono usando sounddevice."""

import queue

import numpy as np
import sounddevice as sd

from speak_now import config


def list_input_devices():
    """Devuelve [(índice, nombre), ...] de los dispositivos con entrada de audio."""
    return [
        (i, dev["name"])
        for i, dev in enumerate(sd.query_devices())
        if dev["max_input_channels"] > 0
    ]


class AudioCapture:
    """Graba del micrófono en segundo plano y entrega bloques de audio por una cola.

    Uso:
        with AudioCapture() as mic:
            for chunk in mic.chunks():
                ...  # chunk es un np.ndarray float32 mono a 16 kHz
    """

    def __init__(self, device=None, sample_rate=config.SAMPLE_RATE,
                 block_duration=config.BLOCK_DURATION):
        self.device = device
        self.sample_rate = sample_rate
        self.block_size = int(sample_rate * block_duration)
        self._queue = queue.Queue()
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

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def read_block(self, timeout=None):
        """Devuelve el siguiente bloque pequeño (BLOCK_DURATION segundos)."""
        return self._queue.get(timeout=timeout)

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


def rms_level(audio):
    """Volumen (RMS) de un bloque de audio, útil para medir si hay voz."""
    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
