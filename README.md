# PyVocoder 🎛️

A desktop vocoder GUI built in Python. Load audio files, video files, or YouTube URLs as your modulator or carrier — or use your microphone live for real-time vocoding straight to any output device.

## Download

👉 **[Download the latest Windows installer from Releases](../../releases/latest)**

The installer includes everything except ffmpeg (see below). No Python required.

> **Note:** Windows may show a SmartScreen warning the first time you run the installer since the app is not code-signed. Click **"More info" → "Run anyway"** to proceed.

---

## What is a vocoder?

A vocoder takes two audio signals — a **modulator** (usually a voice) and a **carrier** (usually a synth or drone) — and imprints the spectral shape of the modulator onto the carrier. The result is the classic "robot voice" effect used in electronic music, film, and broadcasting.

---

## Features

- **Flexible sources** — local audio/video files (WAV, MP3, MP4, MKV, and more), YouTube URLs, or live microphone input, usable as either modulator or carrier
- **Real-time live mode** — speak into your mic and hear the vocoded output instantly through any output device
- **Offline processing** — process two pre-loaded sources and export the result as WAV
- **Output device selection** — route output to any device including virtual audio cables (VB-Audio, BlackHole) for use in Discord, Zoom, OBS, etc.
- **Vocoder controls** — band count, dry/wet mix, carrier pitch shift, envelope attack/release, and formant scaling
- **Live waveform display** and input/output level meters

---

## Installation (Windows)

### Step 1 — Run the installer

Download `PyVocoder.exe` from the [Releases page](../../releases/latest) and run it. It will install PyVocoder and create a Start Menu shortcut.

### Step 2 — Install ffmpeg (required)

ffmpeg handles audio extraction from video files and is not bundled with the installer due to its size.

**Recommended — winget (Windows 10/11):**
```
winget install ffmpeg
```

**Or download manually** from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your PATH.

To verify ffmpeg is installed, open a terminal and run:
```
ffmpeg -version
```

### Step 3 — Launch

Open **PyVocoder** from the Start Menu. The app will show a warning at the top if ffmpeg or yt-dlp is missing.

---

## Usage

### Offline mode
1. Set your **Modulator** source — the signal that shapes the sound (typically a voice recording)
2. Set your **Carrier** source — the signal that gets shaped (typically a synth, pad, or drone)
3. Adjust the vocoder controls
4. Press **▶ Process** — wait for processing to complete
5. Press **▷ Play** to preview, or **💾 Export WAV** to save

### Live mic mode
1. Set **Modulator** → **Microphone (live)** and choose your input device
2. Set **Carrier** → any file or YouTube URL and load it
3. Choose your **Output Device** (speakers, headphones, or a virtual cable)
4. Press **🎙 Live Start** — speak into your mic to hear the effect in real time
5. Tweak controls while live — changes apply instantly
6. Press **■ Live Stop** when done

### Streaming your robot voice into Discord / Zoom / OBS

1. Install a virtual audio cable:
   - [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (free, Windows)
2. In PyVocoder, set **Output Device** to **CABLE Input (VB-Audio)**
3. In Discord / Zoom / OBS, set your microphone input to **CABLE Output (VB-Audio)**
4. Start Live mode in PyVocoder — your vocoded voice now appears as a mic in any app

---

## Controls

| Control | Range | Description |
|---|---|---|
| Bands | 4 – 64 | Number of bandpass filter pairs. More bands = more detailed vocoding, but slower in offline mode |
| Mix | 0 – 100% | Dry/wet blend between the original modulator and the vocoded output |
| Pitch | −12 – +12 st | Shifts the carrier up or down in semitones before vocoding |
| Attack | 1 – 500 ms | How quickly the envelope follower responds to louder transients |
| Release | 1 – 500 ms | How quickly the envelope follower decays after the signal drops |
| Formant | 0.5 – 2.0× | Spectral shift on the output — raises or lowers the tonal character |

---

## Fun things to try

- **Voice + synth pad** → classic Daft Punk / robot vocoder
- **Voice + white noise** → breathy, whispered effect
- **Drums + synth** → rhythmically gated carrier
- **Song vocal (mod) + another song (carrier)** → wild spectral morphing
- **Voice + your own voice** → harmonic doubling / chorus effect

---

## Building from source

If you'd rather run from source or build the installer yourself:

### Requirements

```
pip install pyqt6 numpy scipy soundfile sounddevice pyinstaller
pip install yt-dlp
```

Plus `ffmpeg` on your PATH (see above).

### Run from source

```bash
python pyvocoder.py
```

### Build the Windows installer

Requires [NSIS](https://nsis.sourceforge.io/Download) installed on your system.

```bash
# 1. Bundle with PyInstaller
pyinstaller pyvocoder.spec

# 2. Build the NSIS installer
makensis installer.nsi
```

The output installer will be at `dist/PyVocoder-Setup.exe`.

See [`BUILD.md`](BUILD.md) for detailed build instructions.

---

## License

MIT — see [LICENSE](LICENSE)
