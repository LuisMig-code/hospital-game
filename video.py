"""Vídeo da troca de andar (o elevador por dentro, portas abrindo para a luz).

O pygame não toca vídeo: os quadros são lidos do .mp4 com o OpenCV
(`opencv-python-headless`), um de cada vez, na hora de mostrar. O som foi
extraído para um .wav (`tools/extract_video_audio.py`) e toca no mixer do
pygame. Sem OpenCV (ou sem o arquivo), `FloorVideo.open` devolve None e o
jogo usa a tela escura com "Andar N" no lugar.
"""
import pygame

import settings as S

try:
    import cv2
except ImportError:          # sem OpenCV: troca de andar sem vídeo
    cv2 = None


class FloorVideo:
    def __init__(self, capture, size):
        self.cap = capture
        self.fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
        self.frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.frames / self.fps
        self.size = size
        self.time = 0.0
        self.index = -1           # último quadro lido
        self.surface = None
        self.sound = None

    @classmethod
    def open(cls, path=None, size=(S.SCREEN_W, S.SCREEN_H)):
        if cv2 is None:
            return None
        cap = cv2.VideoCapture(str(path or S.FLOOR_VIDEO))
        if not cap.isOpened() or not cap.get(cv2.CAP_PROP_FRAME_COUNT):
            return None
        return cls(cap, size)

    @property
    def done(self):
        return self.time >= self.duration

    def play_sound(self):
        """Toca o som do vídeo (se houver mixer e o .wav existir)."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.sound = pygame.mixer.Sound(str(S.FLOOR_VIDEO_SOUND))
            self.sound.set_volume(S.FLOOR_VIDEO_VOLUME)
            self.sound.play()
        except (pygame.error, FileNotFoundError):
            self.sound = None

    def update(self, dt):
        """Avança o tempo e lê os quadros até o quadro desse instante."""
        self.time += dt
        want = min(self.frames - 1, int(self.time * self.fps))
        frame = None
        while self.index < want:
            ok, img = self.cap.read()
            if not ok:
                self.time = self.duration       # acabou antes do esperado
                break
            self.index += 1
            frame = img
        if frame is not None:
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)          # OpenCV lê em BGR
            surf = pygame.image.frombytes(rgb.tobytes(), (w, h), "RGB")
            if (w, h) != self.size:
                surf = pygame.transform.smoothscale(surf, self.size)
            self.surface = surf

    def close(self):
        if self.sound is not None:
            self.sound.stop()
        self.cap.release()
