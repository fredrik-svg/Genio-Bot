import queue
import numpy as np
import sounddevice as sd
import webrtcvad

class AudioStream:
    def __init__(self, sample_rate=16000, channels=1, chunk_ms=30, device=None, vad_enabled=True, vad_aggressiveness=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        self.device = device
        self.q = queue.Queue()
        self.vad_enabled = vad_enabled
        self.vad = webrtcvad.Vad(vad_aggressiveness) if vad_enabled else None
        self._stream = None

    def _callback(self, indata, frames, time, status):
        if status:
            # drop status to avoid noise in logs
            pass
        # mono float32 -> int16
        audio = (indata[:, 0] * 32767).astype(np.int16)
        self.q.put(bytes(audio))

    def start(self):
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            dtype="float32",
            callback=self._callback,
            blocksize=self.chunk_size,
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read_frames_until_silence(self, min_voice_ms=300, max_record_ms=10000, silence_ms=800):
        """Returnerar en bytearray med ett helt yttrande (talsegment)."""
        voiced = bytearray()
        voiced_ms = 0
        silence_acc = 0
        while True:
            chunk = self.q.get()
            is_speech = True
            if self.vad:
                is_speech = self.vad.is_speech(chunk, self.sample_rate)
            if is_speech:
                voiced.extend(chunk)
                voiced_ms += int(len(chunk) / 2 / self.sample_rate * 1000)
                silence_acc = 0
            else:
                silence_acc += int(len(chunk) / 2 / self.sample_rate * 1000)
            if voiced_ms >= min_voice_ms and silence_acc >= silence_ms:
                break
            if voiced_ms >= max_record_ms:
                break
        return bytes(voiced)
