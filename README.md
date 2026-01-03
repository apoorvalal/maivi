# Maivi

Maivi is a cross-platform desktop app for real-time voice-to-text with a global
hotkey. It records audio in overlapping chunks and streams transcription results
to an overlay and your clipboard.

## Features

- Global hotkey recording (default: `super+alt+space`, configurable)
- Real-time transcription with an optional overlay
- Streaming chunking with overlap-based merging
- CPU-only by default (no GPU required)

## Installation

CPU-only (recommended):
```bash
pip install maivi --extra-index-url https://download.pytorch.org/whl/cpu
```

Standard install:
```bash
pip install maivi
```

## System Requirements

Linux:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

macOS:
Grant Microphone, Accessibility, and Input Monitoring permissions on first run.

Windows:
PortAudio is usually included with PyAudio.

## Usage

GUI:
```bash
maivi
```

CLI (toggle mode by default):
```bash
maivi-cli
```

Hold-to-record:
```bash
maivi-cli --hold
```

Common options:
```bash
maivi-cli --show-ui
maivi-cli --window 7 --slide 3 --delay 2
maivi-cli --output-file transcription.txt
```

Exit the CLI with Ctrl+C. Quit the GUI from the system tray menu.

## Notes

- The first run downloads the model (~600MB).
- Hotkey, audio parameters, and UI options can be changed in Settings.

## Development

```bash
git clone https://github.com/MaximeRivest/maivi.git
cd maivi
pip install -e .[dev]
pytest
```

## License

MIT. See `LICENSE`.
