#!/usr/bin/env python3
"""
CLI interface for STT server.
"""

import argparse
from maivi.cli.server import StreamingSTTServer


def main():
    parser = argparse.ArgumentParser(
        description="Voice-to-Text STT Server with keyboard shortcuts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server (clipboard only)
  python cli.py

  # Start server with auto-paste
  python cli.py --auto-paste

  # Use speed adjustment (speak at normal speed, record at 2x)
  python cli.py --speed 2.0

  # Hold mode (hold hotkey to record)
  python cli.py --hold

  # Stream to file for voice command detection
  python cli.py --output-file transcription.txt

  # Show live UI window with transcription (recommended!)
  python cli.py --show-ui

  # Custom UI width
  python cli.py --show-ui --ui-width 50

  # Full featured - toggle mode + UI
  python cli.py --show-ui --ui-width 50

Usage:
  1. Start the server
  2. Press the hotkey once to start, again to stop (default)
  3. Use --hold to record only while the hotkey is held
  4. Text is copied to clipboard
  5. If --auto-paste is enabled, text is pasted automatically
  6. Press Ctrl+C to exit

Streaming Mode (SIMPLE OVERLAPPING CHUNKS):
  - Fixed 7s chunks with 4s overlap (3s slide)
  - Processes chunks in parallel during recording
  - Merges using overlap detection (simple and reliable)
  - Nearly instant completion when you stop recording
  - No complex algorithms, just clean overlap-based merging!
        """,
    )

    parser.add_argument(
        "-p",
        "--auto-paste",
        action="store_true",
        help="Automatically paste transcribed text after copying to clipboard",
    )

    parser.add_argument(
        "-s",
        "--stream",
        action="store_true",
        help="Deprecated: streaming is always enabled",
    )

    parser.add_argument(
        "--window",
        type=float,
        default=7.0,
        help="Chunk size in seconds (default: 7.0, larger = better quality)",
    )

    parser.add_argument(
        "--slide",
        type=float,
        default=3.0,
        help="Slide interval in seconds (default: 3.0, window-slide = overlap for merging)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay before starting streaming in seconds (default: 2.0)",
    )

    parser.add_argument(
        "--hotkey",
        default="super+alt+space",
        help="Hotkey combination (default: super+alt+space)",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed multiplier for audio (1.25 = 25%% faster, 2.0 = 2x faster, default: 1.0)",
    )

    parser.add_argument(
        "--hold",
        action="store_true",
        help="Hold mode: hold the hotkey to record (default: toggle)",
    )

    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default=None,
        help="Stream transcription to file (for real-time voice command detection)",
    )

    parser.add_argument(
        "--show-ui",
        action="store_true",
        help="Show live transcription UI window",
    )

    parser.add_argument(
        "--ui-width",
        type=int,
        default=30,
        help="Width of live UI in characters (default: 30)",
    )

    parser.add_argument(
        "--no-pause-breaks",
        action="store_true",
        help="Disable automatic paragraph breaks on long pauses (default: enabled)",
    )

    parser.add_argument(
        "--pause-threshold",
        type=float,
        default=1.0,
        help="Minimum pause duration for paragraph break in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Check for FFmpeg (optional but recommended for advanced audio processing)
    from maivi.utils.ffmpeg_installer import ensure_ffmpeg_installed

    ensure_ffmpeg_installed(silent=False)
    print()

    # Create and run streaming STT server
    server = StreamingSTTServer(
        auto_paste=args.auto_paste,
        window_seconds=args.window,
        slide_seconds=args.slide,
        start_delay_seconds=args.delay,
        speed=args.speed,
        toggle_mode=not args.hold,
        hotkey=args.hotkey,
        output_file=args.output_file,
        show_ui=args.show_ui,
        ui_width=args.ui_width,
        pause_paragraph_breaks=not args.no_pause_breaks,
        pause_threshold_seconds=args.pause_threshold,
    )

    server.run()


if __name__ == "__main__":
    main()
