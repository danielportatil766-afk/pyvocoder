# Building PyVocoder from Source

This guide explains how to produce the `PyVocoder-Setup.exe` Windows installer from the source code.

## Prerequisites

Install these before starting:

| Tool | Purpose | Get it |
|---|---|---|
| Python 3.10+ (64-bit) | Runtime | [python.org](https://www.python.org/downloads/) |
| ffmpeg | Audio extraction | `winget install ffmpeg` |
| NSIS 3.x | Builds the installer | [nsis.sourceforge.io](https://nsis.sourceforge.io/Download) |

Then install Python dependencies:

```bash
pip install pyqt6 numpy scipy soundfile sounddevice pyinstaller
pip install yt-dlp
```

## Build steps

### 1. Bundle with PyInstaller

```bash
pyinstaller pyvocoder.spec
```

This produces a `dist\PyVocoder\` folder containing the self-contained app (no Python needed on the target machine).

**If PyInstaller misses a module**, add it to `hiddenimports` in `pyvocoder.spec` and re-run.

**Test the bundle before packaging:**
```bash
dist\PyVocoder\PyVocoder.exe
```
Make sure it launches correctly and all features work.

### 2. Build the installer with NSIS

```bash
makensis installer.nsi
```

The finished installer will be at:
```
dist\PyVocoder-Setup.exe
```

## Customising before release

Before building for a public release, update these values in `installer.nsi`:

```nsi
!define APP_VERSION     "1.0.0"       ; bump this for each release
!define APP_PUBLISHER   "YourName"    ; your name or org
!define APP_URL         "https://github.com/yourusername/pyvocoder"
```

And in `pyvocoder.spec`, uncomment the icon line if you have one:
```python
# icon='assets/icon.ico',
```

## GitHub Actions (optional — automated builds)

If you want GitHub to build the installer automatically on every push to a release tag, add `.github/workflows/build.yml`:

```yaml
name: Build Windows installer

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pyqt6 numpy scipy soundfile sounddevice pyinstaller yt-dlp

      - name: Install NSIS
        run: choco install nsis

      - name: Build with PyInstaller
        run: pyinstaller pyvocoder.spec

      - name: Build installer with NSIS
        run: makensis installer.nsi

      - name: Upload installer to release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/PyVocoder-Setup.exe
```

With this in place, pushing a tag like `git tag v1.0.0 && git push --tags` will automatically build and attach the installer to a GitHub Release.

## Troubleshooting

**"Failed to execute script"** on launch after PyInstaller bundle:
- Run `dist\PyVocoder\PyVocoder.exe` from a terminal to see the traceback
- Usually a missing hidden import — add it to `pyvocoder.spec`

**sounddevice fails to find PortAudio:**
- PyInstaller should bundle it automatically via the sounddevice hook
- If not, copy `_portaudio.pyd` manually into `dist\PyVocoder\`

**Large installer size:**
- The bundle will typically be 80–150 MB due to Qt and NumPy/SciPy
- UPX compression is enabled in the spec file which helps somewhat
- This is normal for PyQt6 + scientific Python apps
