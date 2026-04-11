#!/usr/bin/env python3
"""
PyVocoder — A flexible vocoder GUI
Supports audio/video files, YouTube URLs, and live microphone input
as modulator or carrier.
"""

import sys
import os
import tempfile
import threading
import subprocess
import collections
import numpy as np
from pathlib import Path

# ── Qt ────────────────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QComboBox, QLineEdit, QFileDialog,
    QFrame, QProgressBar, QMessageBox, QGroupBox, QSizePolicy, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen

# ── Audio ─────────────────────────────────────────────────────────────────────
try:
    import soundfile as sf
    import sounddevice as sd
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

try:
    from scipy.signal import butter, sosfilt, sosfilt_zi
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────
DARK = {
    "bg":       "#0e0f11",
    "surface":  "#16181c",
    "surface2": "#1e2128",
    "border":   "#2a2d35",
    "accent":   "#00e5a0",
    "accent2":  "#7c6cfa",
    "accent3":  "#ff6b6b",
    "accent4":  "#ffb347",
    "text":     "#e8eaf0",
    "text2":    "#8a8fa8",
    "text3":    "#4a4f62",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {DARK["bg"]};
    color: {DARK["text"]};
    font-family: 'Courier New', monospace;
    font-size: 12px;
}}
QGroupBox {{
    background-color: {DARK["surface"]};
    border: 1px solid {DARK["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px;
    font-size: 10px;
    font-weight: bold;
    color: {DARK["text2"]};
    letter-spacing: 2px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {DARK["text2"]};
}}
QPushButton {{
    background-color: {DARK["surface2"]};
    border: 1px solid {DARK["border"]};
    border-radius: 6px;
    padding: 7px 16px;
    color: {DARK["text"]};
    font-family: 'Courier New', monospace;
    font-size: 11px;
}}
QPushButton:hover {{ background-color: {DARK["border"]}; border-color: {DARK["text2"]}; }}
QPushButton:pressed {{ background-color: {DARK["surface"]}; }}
QPushButton#accent  {{ background-color: {DARK["accent"]};  color: #000; border: none; font-weight: bold; letter-spacing: 1px; }}
QPushButton#accent:hover  {{ background-color: #00ffb3; }}
QPushButton#accent2 {{ background-color: {DARK["accent2"]}; color: #fff; border: none; font-weight: bold; }}
QPushButton#accent2:hover {{ background-color: #9a8cff; }}
QPushButton#accent4 {{ background-color: {DARK["accent4"]}; color: #000; border: none; font-weight: bold; letter-spacing: 1px; }}
QPushButton#accent4:hover {{ background-color: #ffc96b; }}
QPushButton#danger  {{ background-color: {DARK["accent3"]}; color: #fff; border: none; font-weight: bold; }}
QPushButton#danger:hover  {{ background-color: #ff9090; }}
QLineEdit {{
    background-color: {DARK["surface2"]};
    border: 1px solid {DARK["border"]};
    border-radius: 5px;
    padding: 6px 10px;
    color: {DARK["text"]};
    font-family: 'Courier New', monospace;
    font-size: 11px;
}}
QLineEdit:focus {{ border-color: {DARK["accent"]}; }}
QSlider::groove:horizontal {{ height: 3px; background: {DARK["border"]}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {DARK["accent"]}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {DARK["accent"]}; border-radius: 2px; }}
QComboBox {{
    background-color: {DARK["surface2"]};
    border: 1px solid {DARK["border"]};
    border-radius: 5px;
    padding: 5px 10px;
    color: {DARK["text"]};
    font-family: 'Courier New', monospace;
    min-width: 100px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {DARK["surface2"]};
    border: 1px solid {DARK["border"]};
    selection-background-color: {DARK["border"]};
    color: {DARK["text"]};
}}
QProgressBar {{
    background-color: {DARK["surface2"]};
    border: 1px solid {DARK["border"]};
    border-radius: 3px;
    height: 5px;
    text-align: center;
    font-size: 10px;
}}
QProgressBar::chunk {{ background-color: {DARK["accent"]}; border-radius: 3px; }}
QLabel#header    {{ font-size: 22px; font-weight: bold; color: {DARK["accent"]}; letter-spacing: 4px; }}
QLabel#subheader {{ font-size: 10px; color: {DARK["text3"]}; letter-spacing: 3px; }}
QLabel#status    {{ font-size: 10px; color: {DARK["text2"]}; padding: 4px 10px; background: {DARK["surface"]}; border: 1px solid {DARK["border"]}; border-radius: 4px; }}
QFrame#divider   {{ background: {DARK["border"]}; max-height: 1px; }}
QCheckBox {{ spacing: 6px; color: {DARK["text2"]}; font-size: 11px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid {DARK["border"]}; background: {DARK["surface2"]}; }}
QCheckBox::indicator:checked {{ background: {DARK["accent"]}; border-color: {DARK["accent"]}; }}
"""

# ─────────────────────────────────────────────────────────────────────────────
# LIVE LEVEL METER
# ─────────────────────────────────────────────────────────────────────────────
class LevelMeter(QWidget):
    def __init__(self, color=DARK["accent"], parent=None):
        super().__init__(parent)
        self.color = color
        self.level = 0.0
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_level(self, rms: float):
        self.level = min(1.0, rms * 6)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(DARK["surface2"]))
        filled = int(w * self.level)
        col = QColor(DARK["accent3"] if self.level > 0.85 else DARK["accent4"] if self.level > 0.65 else self.color)
        p.fillRect(0, 0, filled, h, col)
        p.setPen(QPen(QColor(DARK["border"]), 1))
        p.drawRect(0, 0, w - 1, h - 1)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# WAVEFORM WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class WaveformWidget(QWidget):
    def __init__(self, color=DARK["accent"], parent=None):
        super().__init__(parent)
        self.color   = color
        self.live    = False
        self.samples = np.array([])
        self._ring   = collections.deque(maxlen=600)
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_audio(self, data: np.ndarray):
        mono = data if data.ndim == 1 else data.mean(axis=1)
        n    = min(600, len(mono))
        step = max(1, len(mono) // n)
        self.samples = mono[::step][:n]
        self.update()

    def push_live(self, chunk: np.ndarray):
        mono = chunk if chunk.ndim == 1 else chunk.mean(axis=1)
        step = max(1, len(mono) // 30)
        for s in mono[::step]:
            self._ring.append(float(s))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid  = h // 2
        p.fillRect(0, 0, w, h, QColor(DARK["surface2"]))
        p.setPen(QPen(QColor(DARK["border"]), 1))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 5, 5)
        data = np.array(list(self._ring)) if self.live and len(self._ring) > 0 else self.samples
        if len(data) == 0:
            p.setPen(QPen(QColor(DARK["text3"]), 1))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "no audio loaded")
            p.end()
            return
        col = QColor(self.color)
        col.setAlpha(200)
        p.setPen(QPen(col, 1))
        step_x = w / max(len(data), 1)
        for i, s in enumerate(data):
            x   = int(i * step_x)
            amp = int(np.clip(s, -1, 1) * (h // 2 - 4))
            p.drawLine(x, mid - amp, x, mid + amp)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO LOADER
# ─────────────────────────────────────────────────────────────────────────────
class AudioLoader(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(np.ndarray, int, str)
    error    = pyqtSignal(str)

    def __init__(self, source: str, tmpdir: str):
        super().__init__()
        self.source = source.strip()
        self.tmpdir = tmpdir

    def run(self):
        try:
            path = self._resolve()
            self.progress.emit(80, "Decoding audio…")
            data, sr = self._load_audio(path)
            label = Path(self.source).name if os.path.isfile(self.source) else self.source[:40]
            self.finished.emit(data, sr, label)
        except Exception as e:
            self.error.emit(str(e))

    def _resolve(self) -> str:
        src = self.source
        if src.startswith("http") or "youtube.com" in src or "youtu.be" in src:
            return self._download_yt(src)
        if os.path.isfile(src):
            return src
        raise FileNotFoundError(f"Cannot find: {src}")

    def _download_yt(self, url: str) -> str:
        self.progress.emit(10, "Downloading from YouTube…")
        out = os.path.join(self.tmpdir, "yt_%(id)s.%(ext)s")
        cmd = ["yt-dlp", "-x", "--audio-format", "wav", "--audio-quality", "0",
               "-o", out, "--no-playlist", url]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed:\n{proc.stderr[-600:]}")
        for f in Path(self.tmpdir).glob("yt_*.wav"):
            return str(f)
        for f in Path(self.tmpdir).glob("yt_*"):
            return str(f)
        raise FileNotFoundError("yt-dlp produced no output")

    def _load_audio(self, path: str):
        wav = os.path.join(self.tmpdir, "extracted.wav")
        cmd = ["ffmpeg", "-y", "-i", path, "-vn", "-acodec", "pcm_s16le",
               "-ar", "44100", "-ac", "2", wav]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0 and os.path.isfile(wav):
            data, sr = sf.read(wav)
        else:
            data, sr = sf.read(path)
        return data.astype(np.float32), int(sr)


# ─────────────────────────────────────────────────────────────────────────────
# OFFLINE VOCODER
# ─────────────────────────────────────────────────────────────────────────────
class VocoderProcessor(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(np.ndarray, int)
    error    = pyqtSignal(str)

    def __init__(self, mod, car, sr, params):
        super().__init__()
        self.mod = mod; self.car = car; self.sr = sr; self.params = params

    def run(self):
        try:
            self.finished.emit(self._process(), self.sr)
        except Exception:
            import traceback; self.error.emit(traceback.format_exc())

    def _mono(self, x):
        return x if x.ndim == 1 else x.mean(axis=1)

    def _bp(self, data, lo, hi, sr, order=4):
        nyq = sr / 2
        lo  = max(lo / nyq, 1e-4); hi = min(hi / nyq, 0.9999)
        if lo >= hi: return np.zeros_like(data)
        return sosfilt(butter(order, [lo, hi], btype="band", output="sos"), data)

    def _env(self, sig, att_ms, rel_ms, sr):
        n_a = max(1, int(att_ms * sr / 1000)); n_r = max(1, int(rel_ms * sr / 1000))
        e = np.abs(sig); out = np.zeros_like(e); out[0] = e[0]
        for i in range(1, len(e)):
            a = (1 - np.exp(-2.2 / n_a)) if e[i] > out[i-1] else (1 - np.exp(-2.2 / n_r))
            out[i] = out[i-1] + a * (e[i] - out[i-1])
        return out

    def _pitch(self, car, st, sr):
        if st == 0: return car
        f = 2 ** (st / 12); n = len(car); nn = int(n / f)
        r = np.interp(np.linspace(0, n-1, nn), np.arange(n), car).astype(np.float32)
        return np.pad(r, (0, max(0, n - len(r))))[:n]

    def _process(self):
        p = self.params
        sr = self.sr
        self.progress.emit(5, "Preparing…")
        mod = self._mono(self.mod); car = self._mono(self.car)
        car = self._pitch(car, float(p["pitch"]), sr)
        n   = min(len(mod), len(car)); mod, car = mod[:n], car[:n]
        edges  = np.logspace(np.log10(80), np.log10(min(8000, sr//2-100)), int(p["bands"])+1)
        output = np.zeros(n)
        for i in range(int(p["bands"])):
            self.progress.emit(15 + int(70*i/int(p["bands"])), f"Band {i+1}/{int(p['bands'])}…")
            lo, hi = edges[i], edges[i+1]
            output += self._bp(car, lo, hi, sr) * self._env(self._bp(mod, lo, hi, sr), p["attack"], p["release"], sr)
        self.progress.emit(90, "Normalising…")
        peak = np.max(np.abs(output))
        if peak > 0: output = output / peak * 0.9
        dry = mod / max(np.max(np.abs(mod)), 1e-6) * 0.9
        res = (1 - float(p["mix"])) * dry + float(p["mix"]) * output
        peak = np.max(np.abs(res))
        if peak > 0: res = res / peak * 0.9
        self.progress.emit(100, "Done!")
        return res.astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# REAL-TIME ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class RealtimeVocoder:
    """Frame-by-frame bandpass vocoder with stateful IIR filters."""

    def __init__(self, carrier: np.ndarray, sr: int, params: dict):
        self.sr       = sr
        self._carrier = carrier.astype(np.float32)
        self._car_pos = 0
        self._lock    = threading.Lock()
        self.params   = dict(params)
        self._bands   = []
        self._env_st  = []
        self._build_filters()

    def update_params(self, params: dict):
        with self._lock:
            rebuild = int(params.get("bands", 16)) != len(self._bands)
            self.params = dict(params)
        if rebuild:
            self._build_filters()

    def _build_filters(self):
        sr      = self.sr
        n_bands = int(self.params.get("bands", 16))
        edges   = np.logspace(np.log10(80), np.log10(min(8000, sr//2-100)), n_bands+1)
        bands   = []
        for i in range(n_bands):
            lo = max(edges[i]   / (sr/2), 1e-4)
            hi = min(edges[i+1] / (sr/2), 0.9999)
            if lo < hi:
                sos = butter(2, [lo, hi], btype="band", output="sos")
                zi  = sosfilt_zi(sos)
                bands.append({"sos": sos, "mod_zi": zi.copy(), "car_zi": zi.copy()})
            else:
                bands.append(None)
        with self._lock:
            self._bands  = bands
            self._env_st = np.zeros(n_bands)

    def _carrier_chunk(self, n: int) -> np.ndarray:
        car = self._carrier; total = len(car)
        if total == 0: return np.zeros(n, np.float32)
        out = np.empty(n, np.float32); filled = 0
        while filled < n:
            take = min(n - filled, total - self._car_pos)
            out[filled:filled+take] = car[self._car_pos:self._car_pos+take]
            filled += take; self._car_pos += take
            if self._car_pos >= total: self._car_pos = 0
        return out

    def process_frame(self, mod_frame: np.ndarray) -> np.ndarray:
        mod = mod_frame.ravel().astype(np.float32)
        n   = len(mod)
        with self._lock:
            p   = self.params
            mix = float(p.get("mix", 0.8))
            att = float(p.get("attack",  30))
            rel = float(p.get("release", 100))
            pst = float(p.get("pitch",    0))
            sr  = self.sr
            bands   = self._bands
            env_st  = self._env_st

        car = self._carrier_chunk(n)
        if pst != 0:
            fac = 2 ** (pst / 12); nn = int(n / fac)
            if nn > 0 and nn != n:
                ext = self._carrier_chunk(nn)
                car = np.interp(np.linspace(0, nn-1, n), np.arange(nn), ext).astype(np.float32)

        n_att = max(1, int(att * sr / 1000))
        n_rel = max(1, int(rel * sr / 1000))
        a_att = 1.0 - np.exp(-2.2 / n_att)
        a_rel = 1.0 - np.exp(-2.2 / n_rel)

        output = np.zeros(n, np.float32)
        with self._lock:
            for idx, band in enumerate(bands):
                if band is None: continue
                mb, band["mod_zi"] = sosfilt(band["sos"], mod, zi=band["mod_zi"])
                cb, band["car_zi"] = sosfilt(band["sos"], car, zi=band["car_zi"])
                e_out = np.empty(n); st = env_st[idx]
                for k in range(n):
                    a   = a_att if abs(mb[k]) > st else a_rel
                    st += a * (abs(mb[k]) - st)
                    e_out[k] = st
                env_st[idx] = st
                output += cb * e_out
            self._env_st = env_st

        peak = np.max(np.abs(output))
        if peak > 1e-6: output = output / peak * 0.9
        return ((1 - mix) * mod + mix * output).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# LIVE CONTROLLER THREAD
# ─────────────────────────────────────────────────────────────────────────────
class LiveVocoderController(QThread):
    level_in   = pyqtSignal(float)
    level_out  = pyqtSignal(float)
    chunk_out  = pyqtSignal(np.ndarray)
    error      = pyqtSignal(str)
    started_ok = pyqtSignal()

    BLOCK = 1024

    def __init__(self, carrier, sr, params, mic_device=None, out_device=None):
        super().__init__()
        self.carrier    = carrier
        self.sr         = sr
        self.params     = params
        self.mic_device = mic_device
        self.out_device = out_device
        self._running   = False
        self._engine    = None

    def update_params(self, params):
        if self._engine:
            self._engine.update_params(params)

    def stop(self):
        self._running = False

    def run(self):
        if not (HAS_AUDIO and HAS_SCIPY):
            self.error.emit("sounddevice or scipy not available"); return
        self._engine  = RealtimeVocoder(self.carrier, self.sr, self.params)
        self._running = True
        self.started_ok.emit()
        try:
            with sd.Stream(
                samplerate = self.sr,
                blocksize  = self.BLOCK,
                dtype      = "float32",
                channels   = 1,
                device     = (self.mic_device, self.out_device),
                latency    = "low",
                callback   = self._cb,
            ):
                while self._running:
                    self.msleep(40)
        except Exception as e:
            self.error.emit(str(e))

    def _cb(self, indata, outdata, frames, time, status):
        mod = indata[:, 0]
        out = self._engine.process_frame(mod)
        outdata[:, 0] = out
        self.level_in.emit(float(np.sqrt(np.mean(mod**2))))
        self.level_out.emit(float(np.sqrt(np.mean(out**2))))
        self.chunk_out.emit(out.copy())


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE PANEL
# ─────────────────────────────────────────────────────────────────────────────
class SourcePanel(QGroupBox):
    loaded = pyqtSignal(np.ndarray, int, str)

    def __init__(self, title, color, tmpdir, allow_mic=False, parent=None):
        super().__init__(title, parent)
        self.color     = color
        self.tmpdir    = tmpdir
        self.allow_mic = allow_mic
        self.data      = None
        self.sr        = 44100
        self.is_mic    = False
        self._current_path = ""
        self._loader   = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(8)

        # type selector
        row = QHBoxLayout()
        self.type_combo = QComboBox()
        items = ["File (audio/video)", "YouTube URL"]
        if self.allow_mic: items.append("Microphone (live)")
        self.type_combo.addItems(items)
        self.type_combo.currentIndexChanged.connect(self._on_type)
        row.addWidget(QLabel("Source:")); row.addWidget(self.type_combo, 1)
        lay.addLayout(row)

        # file row
        self.file_row = QWidget()
        fr = QHBoxLayout(self.file_row); fr.setContentsMargins(0,0,0,0)
        self.file_label = QLabel("—")
        self.file_label.setStyleSheet(f"color:{DARK['text2']};font-size:11px;")
        self.browse_btn = QPushButton("Browse…"); self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self._browse)
        fr.addWidget(self.file_label, 1); fr.addWidget(self.browse_btn)
        lay.addWidget(self.file_row)

        # url row
        self.url_row = QWidget(); self.url_row.hide()
        ur = QHBoxLayout(self.url_row); ur.setContentsMargins(0,0,0,0)
        self.url_edit = QLineEdit(); self.url_edit.setPlaceholderText("https://youtube.com/watch?v=…")
        self.fetch_btn = QPushButton("Fetch"); self.fetch_btn.setFixedWidth(60)
        self.fetch_btn.clicked.connect(self._load)
        ur.addWidget(self.url_edit, 1); ur.addWidget(self.fetch_btn)
        lay.addWidget(self.url_row)

        # mic row
        self.mic_row = QWidget(); self.mic_row.hide()
        mr = QHBoxLayout(self.mic_row); mr.setContentsMargins(0,0,0,0)
        self.mic_combo = QComboBox()
        self._populate_mics()
        mr.addWidget(QLabel("Device:")); mr.addWidget(self.mic_combo, 1)
        lay.addWidget(self.mic_row)

        # progress + status
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0)
        self.progress.setMaximumHeight(5); lay.addWidget(self.progress)
        self.status_lbl = QLabel("No source loaded"); self.status_lbl.setObjectName("status")
        lay.addWidget(self.status_lbl)

        # waveform
        self.waveform = WaveformWidget(color=self.color); lay.addWidget(self.waveform)

        # level meter (mic mode only)
        self.meter = LevelMeter(color=self.color); self.meter.hide(); lay.addWidget(self.meter)

        # load btn
        self.load_btn = QPushButton("⬇  Load")
        self.load_btn.setObjectName("accent" if self.color == DARK["accent"] else "accent2")
        self.load_btn.clicked.connect(self._load)
        lay.addWidget(self.load_btn)

    def _populate_mics(self):
        self.mic_combo.clear(); self.mic_combo.addItem("Default input", None)
        if not HAS_AUDIO: return
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    self.mic_combo.addItem(f"{i}: {d['name']}", i)
        except Exception: pass

    def _on_type(self, idx):
        t = ["file","url","mic"][idx] if idx < 3 else "file"
        self.file_row.setVisible(t == "file")
        self.url_row.setVisible(t  == "url")
        self.mic_row.setVisible(t  == "mic")
        self.meter.setVisible(t    == "mic")
        self.is_mic = (t == "mic")
        if t == "mic":
            self.load_btn.setText("✓  Select Mic")
            self._set_status(f"color:{DARK['text2']}", "Mic ready — will activate on Live Start")
        else:
            self.load_btn.setText("⬇  Load")

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select audio/video file", "",
            "Media files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.mp4 *.mkv *.avi *.mov *.webm);;All (*)")
        if path:
            self._current_path = path
            self.file_label.setText(Path(path).name); self.file_label.setToolTip(path)

    def _load(self):
        if self.is_mic:
            self.data = np.zeros(1024, dtype=np.float32)
            self._set_ok("Microphone selected")
            self.loaded.emit(self.data, 44100, "microphone"); return
        src = self._current_path if self.type_combo.currentIndex() == 0 else self.url_edit.text().strip()
        if not src: self.status_lbl.setText("⚠ No source selected"); return
        self.load_btn.setEnabled(False); self.progress.setValue(0)
        self._loader = AudioLoader(src, self.tmpdir)
        self._loader.progress.connect(lambda p,m: (self.progress.setValue(p), self.status_lbl.setText(m)))
        self._loader.finished.connect(self._on_loaded)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def _on_loaded(self, data, sr, label):
        self.data = data; self.sr = sr
        self.waveform.set_audio(data)
        dur = len(data)/sr; ch = "stereo" if data.ndim==2 else "mono"
        self._set_ok(f"{label[:28]}  |  {dur:.1f}s  {ch}  {sr//1000}kHz")
        self.progress.setValue(100); self.load_btn.setEnabled(True)
        self.loaded.emit(data, sr, label)

    def _on_error(self, msg):
        self._set_status(f"color:{DARK['accent3']};padding:4px 10px;background:{DARK['surface']};border:1px solid {DARK['accent3']};border-radius:4px;font-size:10px;", f"✗  {msg[:80]}")
        self.load_btn.setEnabled(True); self.progress.setValue(0)

    def _set_ok(self, msg):
        self._set_status(f"color:{DARK['accent']};padding:4px 10px;background:{DARK['surface']};border:1px solid {DARK['accent']};border-radius:4px;font-size:10px;", f"✓  {msg}")

    def _set_status(self, style, msg):
        self.status_lbl.setStyleSheet(style); self.status_lbl.setText(msg)

    def selected_mic_device(self):
        return self.mic_combo.currentData()


# ─────────────────────────────────────────────────────────────────────────────
# KNOB SLIDER
# ─────────────────────────────────────────────────────────────────────────────
class KnobSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, label, mn, mx, dfl, step=1, fmt="{:.0f}", suffix="", parent=None):
        super().__init__(parent)
        self.fmt = fmt; self.suffix = suffix
        self.int_mult = 100 if step < 1 else 1
        lay = QVBoxLayout(self); lay.setSpacing(2); lay.setContentsMargins(4,4,4,4)
        lbl = QLabel(label); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color:{DARK['text2']};font-size:10px;letter-spacing:1px;")
        lay.addWidget(lbl)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(mn*self.int_mult), int(mx*self.int_mult))
        self.slider.setValue(int(dfl*self.int_mult))
        self.slider.setSingleStep(int(step*self.int_mult))
        self.slider.valueChanged.connect(self._on_change)
        lay.addWidget(self.slider)
        self.val_lbl = QLabel(fmt.format(dfl)+suffix)
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_lbl.setStyleSheet(f"color:{DARK['accent']};font-size:12px;font-weight:bold;")
        lay.addWidget(self.val_lbl)

    def _on_change(self, v):
        r = v / self.int_mult
        self.val_lbl.setText(self.fmt.format(r) + self.suffix)
        self.valueChanged.emit(r)

    def value(self) -> float:
        return self.slider.value() / self.int_mult


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyVocoder")
        self.setMinimumSize(920, 780)
        self.tmpdir       = tempfile.mkdtemp(prefix="pyvocoder_")
        self.result       = None
        self.result_sr    = 44100
        self._processor   = None
        self._live_ctrl   = None
        self._live_active = False
        self._build()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setSpacing(10); root.setContentsMargins(16,16,16,16)

        # header
        hdr = QHBoxLayout()
        t = QLabel("PYVOCODER"); t.setObjectName("header")
        s = QLabel("OFFLINE + LIVE MIC  |  FILE / YOUTUBE / MIC"); s.setObjectName("subheader")
        hdr.addWidget(t); hdr.addSpacing(10); hdr.addWidget(s, 0, Qt.AlignmentFlag.AlignBottom)
        hdr.addStretch()
        self.dep_lbl = QLabel(); self._check_deps(); hdr.addWidget(self.dep_lbl)
        root.addLayout(hdr)
        div = QFrame(); div.setObjectName("divider"); div.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(div)

        # source panels
        src_row = QHBoxLayout()
        self.mod_panel = SourcePanel("MODULATOR (or MIC)", DARK["accent"],  self.tmpdir, allow_mic=True)
        self.car_panel = SourcePanel("CARRIER",            DARK["accent2"], self.tmpdir, allow_mic=False)
        self.mod_panel.loaded.connect(self._on_source_loaded)
        self.car_panel.loaded.connect(self._on_source_loaded)
        src_row.addWidget(self.mod_panel, 1); src_row.addWidget(self.car_panel, 1)
        root.addLayout(src_row)

        swap_row = QHBoxLayout()
        swap_btn = QPushButton("⇄  Swap Modulator ↔ Carrier"); swap_btn.clicked.connect(self._swap)
        swap_row.addStretch(); swap_row.addWidget(swap_btn); swap_row.addStretch()
        root.addLayout(swap_row)

        # controls
        ctrl_box = QGroupBox("VOCODER CONTROLS")
        ctrl_lay = QHBoxLayout(ctrl_box); ctrl_lay.setSpacing(10)
        self.k_bands   = KnobSlider("BANDS",   4,   64,   16, step=1,    fmt="{:.0f}")
        self.k_mix     = KnobSlider("MIX",     0,   1,    0.8, step=0.01, fmt="{:.0%}")
        self.k_pitch   = KnobSlider("PITCH",  -12,  12,   0,  step=0.5,  fmt="{:+.1f}", suffix=" st")
        self.k_attack  = KnobSlider("ATTACK",  1,   500,  30, step=1,    fmt="{:.0f}", suffix=" ms")
        self.k_release = KnobSlider("RELEASE", 1,   500, 100, step=1,    fmt="{:.0f}", suffix=" ms")
        self.k_formant = KnobSlider("FORMANT", 0.5, 2.0,  1.0, step=0.05, fmt="{:.2f}", suffix="×")
        for k in [self.k_bands, self.k_mix, self.k_pitch, self.k_attack, self.k_release, self.k_formant]:
            ctrl_lay.addWidget(k, 1); k.valueChanged.connect(self._on_param_change)
        root.addWidget(ctrl_box)

        # output
        out_box = QGroupBox("OUTPUT"); out_lay = QVBoxLayout(out_box)
        self.out_waveform = WaveformWidget(color=DARK["accent3"]); out_lay.addWidget(self.out_waveform)

        # output device picker
        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Output device:"))
        self.out_dev_combo = QComboBox()
        self._populate_out_devices()
        dev_row.addWidget(self.out_dev_combo, 1)
        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedWidth(32)
        refresh_btn.setToolTip("Refresh device list")
        refresh_btn.clicked.connect(self._refresh_devices)
        dev_row.addWidget(refresh_btn)
        out_lay.addLayout(dev_row)

        # live meters
        mr = QHBoxLayout()
        mr.addWidget(QLabel("MIC IN"))
        self.meter_in = LevelMeter(color=DARK["accent"]); mr.addWidget(self.meter_in, 1)
        mr.addSpacing(12); mr.addWidget(QLabel("OUT"))
        self.meter_out = LevelMeter(color=DARK["accent3"]); mr.addWidget(self.meter_out, 1)
        self.meters_widget = QWidget(); self.meters_widget.setLayout(mr)
        self.meters_widget.hide(); out_lay.addWidget(self.meters_widget)

        self.proc_progress = QProgressBar(); self.proc_progress.setRange(0,100)
        self.proc_progress.setValue(0); self.proc_progress.setMaximumHeight(6)
        out_lay.addWidget(self.proc_progress)
        self.proc_status = QLabel("Waiting for sources…"); self.proc_status.setObjectName("status")
        out_lay.addWidget(self.proc_status)

        btn_row = QHBoxLayout()
        self.process_btn = QPushButton("▶  Process (offline)")
        self.process_btn.setObjectName("accent"); self.process_btn.setMinimumHeight(36)
        self.process_btn.clicked.connect(self._run_offline); btn_row.addWidget(self.process_btn, 2)

        self.live_btn = QPushButton("🎙  Live Start")
        self.live_btn.setObjectName("accent4"); self.live_btn.setMinimumHeight(36)
        self.live_btn.clicked.connect(self._toggle_live); btn_row.addWidget(self.live_btn, 2)

        self.play_btn = QPushButton("▷  Play"); self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play); btn_row.addWidget(self.play_btn, 1)
        self.stop_btn = QPushButton("■  Stop"); self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop); btn_row.addWidget(self.stop_btn, 1)
        self.export_btn = QPushButton("💾  Export WAV"); self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export); btn_row.addWidget(self.export_btn, 1)
        out_lay.addLayout(btn_row); root.addWidget(out_box)

    def _populate_out_devices(self):
        self.out_dev_combo.clear()
        self.out_dev_combo.addItem("Default output", None)
        if not HAS_AUDIO:
            return
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_output_channels"] > 0:
                    self.out_dev_combo.addItem(f"{i}: {d['name']}", i)
        except Exception:
            pass

    def _refresh_devices(self):
        # remember current selections by name
        cur_out = self.out_dev_combo.currentText()
        self._populate_out_devices()
        # try to restore previous selection
        idx = self.out_dev_combo.findText(cur_out)
        if idx >= 0:
            self.out_dev_combo.setCurrentIndex(idx)
        # also refresh mic combos in panels
        self.mod_panel._populate_mics()
        self.proc_status.setText("Device list refreshed")

    def _selected_out_device(self):
        return self.out_dev_combo.currentData()

    def _check_deps(self):
        missing = []
        if not HAS_AUDIO:  missing.append("soundfile/sounddevice")
        if not HAS_SCIPY:  missing.append("scipy")
        for cmd in [["ffmpeg","-version"],["yt-dlp","--version"]]:
            try: subprocess.run(cmd, capture_output=True, check=True)
            except Exception: missing.append(cmd[0])
        if missing:
            self.dep_lbl.setText(f"⚠ Missing: {', '.join(missing)}")
            self.dep_lbl.setStyleSheet(f"color:{DARK['accent3']};font-size:10px;")
        else:
            self.dep_lbl.setText("✓ All deps OK")
            self.dep_lbl.setStyleSheet(f"color:{DARK['accent']};font-size:10px;")

    def _params(self):
        return {k: getattr(self, f"k_{k}").value() for k in ["bands","mix","pitch","attack","release","formant"]}

    def _on_param_change(self, _):
        if self._live_ctrl: self._live_ctrl.update_params(self._params())

    def _on_source_loaded(self, *_):
        if self.mod_panel.data is not None and self.car_panel.data is not None:
            msg = "Mic + carrier ready — press Live Start" if self.mod_panel.is_mic else "Both sources ready — press Process or Live Start"
            self.proc_status.setText(msg)

    def _swap(self):
        if None in (self.mod_panel.data, self.car_panel.data):
            self.proc_status.setText("⚠ Load both sources first"); return
        if self.mod_panel.is_mic:
            self.proc_status.setText("⚠ Cannot swap while mic is selected"); return
        self.mod_panel.data, self.car_panel.data = self.car_panel.data, self.mod_panel.data
        self.mod_panel.sr,   self.car_panel.sr   = self.car_panel.sr,   self.mod_panel.sr
        self.mod_panel.waveform.set_audio(self.mod_panel.data)
        self.car_panel.waveform.set_audio(self.car_panel.data)

    # ── offline ───────────────────────────────────────────────────────────
    def _run_offline(self):
        if self._live_active:
            self.proc_status.setText("⚠ Stop live mode first"); return
        if self.mod_panel.is_mic or self.mod_panel.data is None:
            self.proc_status.setText("⚠ Set a non-mic MODULATOR source for offline processing"); return
        if self.car_panel.data is None:
            self.proc_status.setText("⚠ Load a CARRIER source first"); return
        sr  = self.mod_panel.sr
        mod = self.mod_panel.data
        car = self.car_panel.data
        if self.car_panel.sr != sr:
            ratio = sr / self.car_panel.sr; n_new = int(len(car) * ratio)
            c     = car.mean(axis=1) if car.ndim==2 else car
            car   = np.interp(np.linspace(0,len(c)-1,n_new), np.arange(len(c)), c).astype(np.float32)
        self.process_btn.setEnabled(False); self.proc_progress.setValue(0)
        self._processor = VocoderProcessor(mod, car, sr, self._params())
        self._processor.progress.connect(lambda p,m: (self.proc_progress.setValue(p), self.proc_status.setText(m)))
        self._processor.finished.connect(self._on_offline_done)
        self._processor.error.connect(lambda e: (self.proc_status.setText(f"✗ {e[:100]}"), self.process_btn.setEnabled(True)))
        self._processor.start()

    def _on_offline_done(self, data, sr):
        self.result = data; self.result_sr = sr
        self.out_waveform.live = False
        self.out_waveform.set_audio(data)
        self.proc_progress.setValue(100)
        self.proc_status.setStyleSheet(f"color:{DARK['accent']};font-size:10px;padding:4px 10px;background:{DARK['surface']};border:1px solid {DARK['accent']};border-radius:4px;")
        self.proc_status.setText(f"✓ Done!  {len(data)/sr:.2f}s  @{sr}Hz")
        self.process_btn.setEnabled(True)
        self.play_btn.setEnabled(True); self.export_btn.setEnabled(True)

    # ── live ──────────────────────────────────────────────────────────────
    def _toggle_live(self):
        self._stop_live() if self._live_active else self._start_live()

    def _start_live(self):
        if self.car_panel.data is None:
            self.proc_status.setText("⚠ Load a CARRIER source first"); return
        car = self.car_panel.data
        if car.ndim == 2: car = car.mean(axis=1)
        mic_dev = self.mod_panel.selected_mic_device() if self.mod_panel.is_mic else None
        out_dev = self._selected_out_device()
        self._live_ctrl = LiveVocoderController(
            carrier=car.astype(np.float32), sr=self.car_panel.sr,
            params=self._params(), mic_device=mic_dev, out_device=out_dev)
        self._live_ctrl.level_in.connect(self.meter_in.set_level)
        self._live_ctrl.level_out.connect(self.meter_out.set_level)
        self._live_ctrl.chunk_out.connect(self._on_live_chunk)
        self._live_ctrl.error.connect(self._on_live_error)
        self._live_ctrl.started_ok.connect(self._on_live_started)
        self._live_ctrl.start()

    def _on_live_started(self):
        self._live_active = True
        self.live_btn.setText("■  Live Stop")
        self.live_btn.setStyleSheet(f"background-color:{DARK['accent3']};color:#fff;border:none;font-weight:bold;border-radius:6px;padding:7px 16px;min-height:36px;")
        self.meters_widget.show()
        self.proc_status.setStyleSheet(f"color:{DARK['accent4']};font-size:10px;padding:4px 10px;background:{DARK['surface']};border:1px solid {DARK['accent4']};border-radius:4px;")
        self.proc_status.setText(f"🎙  LIVE — mic → vocoder → {self.out_dev_combo.currentText()[:40]}")

    def _on_live_chunk(self, chunk):
        self.out_waveform.live = True
        self.out_waveform.push_live(chunk)

    def _on_live_error(self, msg):
        self._live_active = False
        self.proc_status.setStyleSheet(f"color:{DARK['accent3']};font-size:10px;padding:4px 10px;background:{DARK['surface']};border:1px solid {DARK['accent3']};border-radius:4px;")
        self.proc_status.setText(f"✗ Live error: {msg[:100]}")
        self._reset_live_btn()

    def _stop_live(self):
        if self._live_ctrl:
            self._live_ctrl.stop(); self._live_ctrl.wait(2000); self._live_ctrl = None
        self._live_active = False
        self.out_waveform.live = False
        self.meters_widget.hide()
        self.meter_in.set_level(0); self.meter_out.set_level(0)
        self.proc_status.setText("Live stopped")
        self._reset_live_btn()

    def _reset_live_btn(self):
        self.live_btn.setText("🎙  Live Start")
        self.live_btn.setStyleSheet(f"background-color:{DARK['accent4']};color:#000;border:none;font-weight:bold;border-radius:6px;padding:7px 16px;letter-spacing:1px;min-height:36px;")

    # ── playback / export ─────────────────────────────────────────────────
    def _play(self):
        if self.result is None or not HAS_AUDIO: return
        try:
            out_dev = self._selected_out_device()
            sd.stop()
            sd.play(self.result, self.result_sr, device=out_dev)
            self.stop_btn.setEnabled(True)
        except Exception as e: self.proc_status.setText(f"Playback error: {e}")

    def _stop(self):
        if HAS_AUDIO: sd.stop()
        self.stop_btn.setEnabled(False)

    def _export(self):
        if self.result is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Export WAV", "vocoder_output.wav", "WAV files (*.wav)")
        if path:
            try: sf.write(path, self.result, self.result_sr); self.proc_status.setText(f"✓ Exported: {Path(path).name}")
            except Exception as e: self.proc_status.setText(f"Export error: {e}")

    def closeEvent(self, ev):
        self._stop_live()
        if HAS_AUDIO:
            try: sd.stop()
            except Exception: pass
        ev.accept()


# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("PyVocoder")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
