"""Extrai o som do vídeo do elevador para um .wav (o mixer do pygame não lê
áudio AAC de dentro de .mp4).

Uso (uma vez; precisa do pacote `av`, só para esta ferramenta):
    venv\\Scripts\\python.exe -m pip install av
    venv\\Scripts\\python.exe tools\\extract_video_audio.py

Saída: settings.FLOOR_VIDEO_SOUND (16 bits, estéreo, 48 kHz).
"""
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import settings as S  # noqa: E402


def main():
    import av
    from av.audio.resampler import AudioResampler

    container = av.open(str(S.FLOOR_VIDEO))
    stream = next(s for s in container.streams if s.type == "audio")
    resampler = AudioResampler(format="s16", layout="stereo", rate=48000)
    pcm = bytearray()
    for frame in container.decode(stream):
        for out in resampler.resample(frame):
            pcm += bytes(out.planes[0])[: out.samples * 4]
    for out in resampler.resample(None):              # o que sobrou no resampler
        pcm += bytes(out.planes[0])[: out.samples * 4]
    with wave.open(str(S.FLOOR_VIDEO_SOUND), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(bytes(pcm))
    print(f"{len(pcm) / 4 / 48000:.2f} s de áudio salvos em {S.FLOOR_VIDEO_SOUND}")


if __name__ == "__main__":
    main()
