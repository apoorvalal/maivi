# Maivi - My AI Voice Input 🎤

**Real-time voice-to-text transcription with hotkey support**

Maivi (My AI Voice Input) is a cross-platform desktop application that turns your voice into text using state-of-the-art AI models. Simply press your configured hotkey (default: **Super+Alt+Space**) to start recording, and press again to stop. Your transcription appears in real-time and is automatically copied to your clipboard.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey.svg)
[![GitHub Release](https://img.shields.io/github/v/release/MaximeRivest/maivi)](https://github.com/MaximeRivest/maivi/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/maivi)](https://pypi.org/project/maivi/)
[![Downloads](https://img.shields.io/github/downloads/MaximeRivest/maivi/total)](https://github.com/MaximeRivest/maivi/releases)

## ✨ Features

- 🎤 **Hotkey Recording** - Toggle recording with your hotkey (default: Super+Alt+Space)
- ⚡ **Real-time Transcription** - See text appear as you speak
- 📋 **Clipboard Integration** - Automatic copy to clipboard
- 🪟 **Floating Overlay** - Live transcription in a sleek overlay window
- 🔄 **Smart Chunk Merging** - Advanced overlap-based merging eliminates duplicates
- 💻 **CPU-Only** - No GPU required (though GPU acceleration is supported)
- 🌍 **High Accuracy** - Powered by NVIDIA Parakeet TDT 0.6B model (~6-9% WER)
- 🚀 **Fast** - ~0.36x RTF (processes 7s audio in 2.5s on CPU)

## 📥 Download

### Pre-built Executables (Recommended)

Download the latest executable for your platform from the [Releases page](https://github.com/MaximeRivest/maivi/releases/latest):

| Platform | Download | Size |
|----------|----------|------|
| 🐧 **Linux** | [maivi-linux](https://github.com/MaximeRivest/maivi/releases/latest/download/maivi-linux) | ~300MB |
| 🍎 **macOS** | [maivi-macos](https://github.com/MaximeRivest/maivi/releases/latest/download/maivi-macos) | ~300MB |
| 🪟 **Windows** | [maivi-windows.exe](https://github.com/MaximeRivest/maivi/releases/latest/download/maivi-windows.exe) | ~300MB |

**Quick Start:**

**Linux/macOS:**
```bash
# Download and make executable
chmod +x maivi-linux  # or maivi-macos
# Run
./maivi-linux  # or ./maivi-macos
```

**Windows:**
- Download `maivi-windows.exe`
- Double-click to run (or run from command prompt)

**First Run Notes:**
- The first time you run Maivi, it will download the AI model (~600MB)
- On macOS, you may need to grant permissions: System Settings → Privacy & Security
- FFmpeg installation will be offered if not already installed (optional)

### Install via pip

Alternatively, install from PyPI:

```bash
pip install maivi --extra-index-url https://download.pytorch.org/whl/cpu
```

See [Installation](#installation) section for more details.

## 🚀 Quick Start

### Installation

**CPU-only (Recommended - much faster, 100MB vs 2GB+):**
```bash
pip install maivi --extra-index-url https://download.pytorch.org/whl/cpu
```

**Or with GPU support (if you have NVIDIA GPU):**
```bash
pip install maivi --extra-index-url https://download.pytorch.org/whl/cu121
```

**Standard install (may download large CUDA files):**
```bash
pip install maivi
```

### System Requirements

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**macOS:**
Grant Maivi microphone, Accessibility, and Input Monitoring permissions the first time you run it (System Settings → Privacy & Security). No additional Homebrew packages are required for audio capture.

**Windows:**
- PortAudio is usually included with PyAudio

### Usage

**GUI Mode (Recommended):**
```bash
maivi
```

Press your hotkey (default: **Super+Alt+Space**) to start recording, press it again to stop. The transcription will appear in a floating overlay and be copied to your clipboard.

**CLI Mode:**
```bash
# Basic CLI
maivi-cli

# With live terminal UI
maia-cli --show-ui

# Custom parameters
maia-cli --window 10 --slide 5 --show-ui
```

**Controls:**
- **Configured hotkey** (default: Super+Alt+Space) - Start/stop recording (toggle mode)
- **Quit** - Use the system tray menu

## 📖 How It Works

Maia uses a sophisticated streaming architecture:

1. **Sliding Window Recording** - Captures audio in overlapping 7-second chunks every 3 seconds
2. **Real-time Transcription** - Each chunk is transcribed by the NVIDIA Parakeet model
3. **Smart Merging** - Chunks are merged using overlap detection (4-second overlap)
4. **Live Updates** - The UI updates in real-time as transcription progresses

### Why Overlapping Chunks?

```
Chunk 1: "hello world how are you"
Chunk 2: "how are you doing today"
          ^^^^^^^^^^^^^^
          Overlap detected → merge!

Result: "hello world how are you doing today"
```

This approach ensures:
- ✅ No words cut mid-syllable
- ✅ Context preserved for better accuracy
- ✅ Seamless merging without duplicates
- ✅ Fast processing (no queue buildup)

## ⚙️ Configuration

### Chunk Parameters

```bash
maia-cli --window 7.0 --slide 3.0 --delay 2.0
```

- `--window`: Chunk size in seconds (default: 7.0)
  - Larger = better quality, slower processing
- `--slide`: Slide interval in seconds (default: 3.0)
  - Smaller = more overlap, higher CPU usage
  - **Rule:** Must be > `window × 0.36` to avoid queue buildup
- `--delay`: Processing start delay in seconds (default: 2.0)

### Advanced Options

```bash
# Speed adjustment (experimental)
maia-cli --speed 1.5

# Custom UI width
maia-cli --show-ui --ui-width 50

# Disable pause detection
maia-cli --no-pause-breaks

# Stream to file (for voice commands)
maia-cli --output-file transcription.txt
```

## 📦 Building from Source

For developers who want to build executables:

```bash
# Install build dependencies
pip install maivi[build]

# Build executable
pyinstaller --onefile \
  --name maivi \
  --add-data "src/maivi:maivi" \
  --hidden-import=nemo \
  --hidden-import=nemo.collections.asr \
  --hidden-import=PySide6 \
  src/maivi/__main__.py
```

Executables are automatically built via GitHub Actions for each release. See [.github/workflows/build-executables.yml](.github/workflows/build-executables.yml) for the full build configuration.

## 🏗️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/MaximeRivest/maivi.git
cd maivi

# Install in development mode
pip install -e .[dev]

# Run tests
pytest
```

### Project Structure

```
maia/
├── src/maia/
│   ├── __init__.py
│   ├── __main__.py           # GUI entry point
│   ├── core/
│   │   ├── streaming_recorder.py
│   │   ├── chunk_merger.py
│   │   └── pause_detector.py
│   ├── gui/
│   │   └── qt_gui.py
│   ├── cli/
│   │   ├── cli.py
│   │   ├── server.py
│   │   └── terminal_ui.py
│   └── utils/
├── tests/
├── docs/
├── pyproject.toml
├── README.md
└── LICENSE
```

## 🐛 Troubleshooting

### "No overlap found" warnings

This is **expected behavior** when there are long pauses (5+ seconds of silence). The system adds "..." gap markers to indicate the pause.

### Queue buildup (transcription continues after stopping)

Check that processing time < slide interval:
- Processing: `window_seconds × 0.36` (RTF)
- Should be < `slide_seconds`
- Default: `7 × 0.36 = 2.52s < 3s` ✅

### Model download issues

The first run downloads the NVIDIA Parakeet model (~600MB) from HuggingFace. If download fails:
- Check internet connection
- Verify HuggingFace is accessible
- Clear cache: `rm -rf ~/.cache/huggingface/`

### Qt/GUI crashes

If the GUI crashes on Linux:
```bash
# Check Qt installation
python -c "from PySide6 import QtWidgets; print('Qt OK')"

# Fall back to CLI mode
maia-cli --show-ui
```

## 📊 Performance

**Memory:**
- Model: ~2GB RAM
- Audio buffer: ~1MB
- Total: ~2.5GB RAM

**CPU:**
- Idle: <5% CPU
- Recording: 30-40% of 1 core
- Transcription: 100% of 1 core (during processing)

**Latency:**
- First transcription: 2s (start delay)
- Updates: Every 3s (slide interval)
- Completion: 1-3s after recording stops

**Accuracy:**
- Model WER: ~5-8%
- Overlap merging: <1% word loss
- Total effective WER: ~6-9%

## 🗺️ Roadmap

**v0.2 - Platform Support:**
- [ ] Test and verify macOS support
- [ ] Test and verify Windows support
- [ ] Platform-specific installers (.app, .exe)

**v0.3 - Features:**
- [ ] Configurable hotkeys via GUI
- [ ] Multi-language support
- [ ] Custom model selection
- [ ] Voice commands support

**v0.4 - Optimization:**
- [ ] GPU acceleration (CUDA)
- [ ] Export formats (JSON, SRT)
- [ ] Text editor integration
- [ ] Plugin system

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [NVIDIA NeMo](https://github.com/NVIDIA/NeMo) ASR toolkit
- Uses [Parakeet TDT 0.6B](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) model
- GUI powered by [PySide6](https://wiki.qt.io/Qt_for_Python)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 💬 Support

- 📫 [Create an issue](https://github.com/MaximeRivest/maivi/issues)
- 💡 [Feature requests](https://github.com/MaximeRivest/maivi/issues/new?labels=enhancement)
- 🐛 [Bug reports](https://github.com/MaximeRivest/maivi/issues/new?labels=bug)

---

Made with ❤️ by [Maxime Rivest](https://github.com/MaximeRivest)
