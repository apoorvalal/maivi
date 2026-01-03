"""
Streaming STT Server with real-time transcription.
Processes audio chunks as they're recorded using a sliding window.
"""

import os
import time
import threading

import pyperclip
import soundfile as sf
from pynput import keyboard
from pynput.keyboard import Key, Controller

from maivi.core.streaming_recorder import StreamingRecorder
from maivi.core.chunk_merger import SimpleChunkMerger  # New simple merger
from maivi.cli.terminal_ui import create_streaming_ui
from maivi.core.pause_detector import PauseDetector
from maivi.utils.torch_jit import disable_torch_jit

# Cross-platform notifications
try:
    from plyer import notification

    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


class StreamingSTTServer:
    def __init__(
        self,
        auto_paste=False,
        window_seconds=7.0,  # Chunk size (more context = better quality)
        slide_seconds=3.0,  # Slide interval (larger overlap = better merging)
        start_delay_seconds=2.0,  # Start processing after this delay
        speed=1.0,
        toggle_mode=True,
        hotkey="super+alt+space",
        output_file=None,
        show_ui=False,
        ui_width=30,
        pause_paragraph_breaks=True,
        pause_threshold_seconds=1.0,
    ):
        self.auto_paste = auto_paste
        self.speed = speed
        self.toggle_mode = toggle_mode
        self.hotkey = hotkey or "super+alt+space"
        self.hotkey_parts = self._parse_hotkey(self.hotkey)
        self.output_file = output_file
        self.model = None

        # Simple fixed overlapping chunks
        self.recorder = StreamingRecorder(
            window_seconds=window_seconds,
            slide_seconds=slide_seconds,
            start_delay_seconds=start_delay_seconds,
            speed=speed,
        )
        self.keyboard_controller = Controller()
        self.is_shutting_down = False

        # Track which keys are pressed for hotkey detection
        self.current_keys = set()
        self.hotkey_pressed = False
        self.is_recording = False  # For toggle mode

        # Transcription state
        self.transcription_thread = None
        self.chunk_counter = 0
        self.chunk_merger = SimpleChunkMerger()  # Simple overlap-based merging
        self.is_transcribing = False

        # Output file handle
        self.output_stream = None
        if self.output_file:
            self.output_stream = open(
                self.output_file, "w", buffering=1
            )  # Line buffered

        # Streaming UI
        self.show_ui = show_ui
        self.streaming_ui = None
        if self.show_ui:
            self.streaming_ui = create_streaming_ui(
                width_chars=ui_width, prefer_gui=True
            )

        # Pause detection for paragraph breaks
        self.pause_paragraph_breaks = pause_paragraph_breaks
        self.pause_detector = PauseDetector(
            silence_threshold_db=-40.0,
            min_pause_duration=pause_threshold_seconds,
            sample_rate=16000,
        )
        self.last_chunk_audio = None  # Store last chunk audio for pause detection
        self.recording_start_time = None  # Track when recording started

    def _parse_hotkey(self, hotkey_str):
        """Parse hotkey string into component parts."""
        cleaned = (hotkey_str or "").replace("<", "").replace(">", "").lower()
        parts = [p.strip() for p in cleaned.split("+") if p.strip()]
        aliases = {
            "control": "ctrl",
            "option": "alt",
            "command": "meta",
            "cmd": "meta",
            "super": "meta",
            "win": "meta",
            "windows": "meta",
            "spacebar": "space",
        }
        normalized = [aliases.get(part, part) for part in parts]
        modifiers = set()
        keys = []
        for part in normalized:
            if part in ["ctrl", "alt", "shift", "meta"]:
                modifiers.add(part)
            else:
                keys.append(part)
        return {"modifiers": modifiers, "keys": keys}

    def _check_hotkey_pressed(self):
        """Check if the configured hotkey combination is currently pressed."""
        modifiers_pressed = set()
        if (
            Key.ctrl_l in self.current_keys
            or Key.ctrl in self.current_keys
            or Key.ctrl_r in self.current_keys
        ):
            modifiers_pressed.add("ctrl")
        if (
            Key.alt_l in self.current_keys
            or Key.alt in self.current_keys
            or Key.alt_r in self.current_keys
        ):
            modifiers_pressed.add("alt")
        if (
            Key.shift_l in self.current_keys
            or Key.shift in self.current_keys
            or Key.shift_r in self.current_keys
        ):
            modifiers_pressed.add("shift")
        if hasattr(Key, "cmd") and (
            Key.cmd in self.current_keys
            or Key.cmd_l in self.current_keys
            or Key.cmd_r in self.current_keys
        ):
            modifiers_pressed.add("meta")

        if modifiers_pressed != self.hotkey_parts["modifiers"]:
            return False

        if not self.hotkey_parts["keys"]:
            return True

        for required_key in self.hotkey_parts["keys"]:
            key_found = False
            try:
                if keyboard.KeyCode.from_char(required_key) in self.current_keys:
                    key_found = True
                if required_key == "q" and keyboard.KeyCode.from_char("œ") in self.current_keys:
                    key_found = True
            except Exception:
                pass

            special_keys = {
                "space": Key.space,
                "return": Key.enter,
                "enter": Key.enter,
                "tab": Key.tab,
                "backspace": Key.backspace,
                "delete": Key.delete,
                "home": Key.home,
                "end": Key.end,
                "pageup": Key.page_up,
                "pagedown": Key.page_down,
                "up": Key.up,
                "down": Key.down,
                "left": Key.left,
                "right": Key.right,
            }
            if hasattr(Key, "insert"):
                special_keys["insert"] = Key.insert

            for i in range(1, 13):
                special_keys[f"f{i}"] = getattr(Key, f"f{i}", None)

            if required_key in special_keys and special_keys[required_key] in self.current_keys:
                key_found = True

            if not key_found:
                return False

        return True

    def _show_notification(self, title: str, message: str, timeout: int = 2):
        """Show cross-platform notification (non-blocking)."""
        if not NOTIFICATIONS_AVAILABLE:
            return

        try:
            notification.notify(
                title=title,
                message=message,
                app_name="STT Server",
                timeout=timeout,  # seconds
            )
        except Exception:
            # Silently fail if notifications don't work
            pass

    def load_model(self):
        """Load the STT model."""
        print("Loading Parakeet TDT 0.6B v3 model...")
        print("This may take a few minutes on first run (downloading model)...")

        # Force CPU usage
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        disable_torch_jit()

        try:
            import nemo.collections.asr as nemo_asr
        except Exception as exc:
            print("❌ Failed to import NeMo ASR.")
            print(f"   Error: {exc}")
            print(
                "   If you're running a bundled binary, TorchScript may be blocked by"
                " missing source files."
            )
            return False

        start_time = time.time()
        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v3"
        )
        self.model = self.model.cpu()
        self.model.eval()

        load_time = time.time() - start_time
        print(f"✓ Model loaded in {load_time:.2f} seconds\n")
        return True

    def transcribe_chunk(self, chunk_np, chunk_id, is_last_chunk=False):
        """Transcribe a single audio chunk and merge with existing result."""
        try:
            # Save chunk to file
            chunk_file = self.recorder.save_chunk_to_file(chunk_np, chunk_id)
            if not chunk_file:
                return None

            # Transcribe
            start_time = time.time()
            output = self.model.transcribe([chunk_file], timestamps=False)
            text = output[0].text.strip()
            transcribe_time = time.time() - start_time

            if text:
                # Merge with existing result using overlap detection
                merged = self.chunk_merger.add_chunk(text, is_final=is_last_chunk)

                # Show progress
                marker = "🏁" if is_last_chunk else "⚡"
                print(f"  {marker} Chunk {chunk_id}: {text[:50]}...")
                print(f"     Merged ({len(merged.split())} words): ...{merged[-80:]}")

                # Stream to file if enabled
                if self.output_stream:
                    self.output_stream.write(f"{merged}\n")
                    self.output_stream.flush()

                # Update streaming UI if enabled
                if self.streaming_ui:
                    self.streaming_ui.update_text(merged)

                return text
            return None

        except Exception as e:
            print(f"Error transcribing chunk {chunk_id}: {e}")
            return None

    def streaming_transcription_loop(self):
        """
        Process audio chunks with simple fixed overlapping windows.

        Strategy:
        - Fixed 7s windows sliding every 3s (4s overlap)
        - Merge using overlap detection (simple and reliable)
        - Process chunks as they arrive during recording
        """
        print("🔄 Streaming processor started")
        print(
            f"   Window: {self.recorder.window_seconds}s, Slide: {self.recorder.slide_seconds}s"
        )
        print(
            f"   Overlap: {self.recorder.window_seconds - self.recorder.slide_seconds}s"
        )

        self.chunk_counter = 0
        self.chunk_merger.reset()

        while self.is_transcribing or not self.recorder.processing_queue.empty():
            chunk_np = self.recorder.get_next_chunk()

            if chunk_np is not None:
                self.chunk_counter += 1
                is_last = (
                    not self.is_transcribing and self.recorder.processing_queue.empty()
                )

                # Transcribe this chunk
                self.transcribe_chunk(
                    chunk_np, self.chunk_counter, is_last_chunk=is_last
                )
            else:
                # No chunk available yet
                time.sleep(0.1)

        print("🔄 Streaming processor stopped")

    def _normalize_text(self, text):
        """Normalize text (same as chunk_merger)."""
        import re

        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return " ".join(text.split())

    def _transcribe_full_recording(self, audio_file: str) -> str | None:
        """Transcribe a full recording as a fallback."""
        if self.model is None:
            print("❌ Error: Model failed to load")
            return None
        try:
            output = self.model.transcribe([audio_file], timestamps=False)
            return output[0].text.strip()
        except Exception as exc:
            print(f"Error transcribing: {exc}")
            return None

    def _handle_final_text(self, final_text: str | None) -> bool:
        """Print, copy, and optionally paste the final transcription."""
        if not final_text:
            print("No text transcribed")
            return False

        print(f"\n{'=' * 60}")
        print("📝 Final Transcription:")
        print(f"{'=' * 60}")
        print(final_text)
        print(f"{'=' * 60}\n")

        # Copy to clipboard
        pyperclip.copy(final_text)
        print("✓ Copied to clipboard")

        # Small delay to ensure notification shows before auto-paste
        time.sleep(0.1)

        # Auto-paste if enabled
        if self.auto_paste:
            time.sleep(0.2)
            self.keyboard_controller.press(Key.ctrl)
            self.keyboard_controller.press("v")
            self.keyboard_controller.release("v")
            self.keyboard_controller.release(Key.ctrl)
            print("✓ Auto-pasted")

        print()
        return True

    def finalize_transcription(self, final_text: str | None = None):
        """Finalize and output the complete transcription."""
        if final_text is None:
            final_text = self.chunk_merger.get_result()
        self._handle_final_text(final_text)

    def on_press(self, key):
        """Handle key press events."""
        if self.is_shutting_down:
            return False

        # Track pressed keys
        try:
            self.current_keys.add(key)
        except:
            pass

        hotkey_combo = self._check_hotkey_pressed()

        if self.toggle_mode:
            # Toggle mode: press once to start, press again to stop
            if hotkey_combo and not self.hotkey_pressed:
                self.hotkey_pressed = True  # Debounce

                if not self.is_recording:
                    # Start recording
                    print("🔴 Recording started (press again to stop)")
                    self.chunk_counter = 0
                    self.recording_start_time = (
                        time.time()
                    )  # Track start time for hybrid mode

                    self.recorder.start_recording()
                    if not self.recorder.is_recording:
                        print("❌ Recording failed to start.")
                        self.hotkey_pressed = False
                        return

                    self.is_recording = True
                    # Start streaming UI if enabled
                    if self.streaming_ui:
                        self.streaming_ui.start()

                    self.is_transcribing = True
                    self.transcription_thread = threading.Thread(
                        target=self.streaming_transcription_loop
                    )
                    self.transcription_thread.start()
                else:
                    # Stop recording
                    self._stop_recording()
        else:
            # Hold mode: hold to record, release to stop
            if hotkey_combo:
                if not self.hotkey_pressed and not self.recorder.is_recording:
                    self.hotkey_pressed = True
                    self.chunk_counter = 0
                    self.recording_start_time = (
                        time.time()
                    )  # Track start time for hybrid mode

                    # Start recording
                    self.recorder.start_recording()
                    if not self.recorder.is_recording:
                        print("❌ Recording failed to start.")
                        self.hotkey_pressed = False
                        return

                    # Start streaming UI if enabled
                    if self.streaming_ui:
                        self.streaming_ui.start()

                    # Start transcription loop
                    self.is_transcribing = True
                    self.transcription_thread = threading.Thread(
                        target=self.streaming_transcription_loop
                    )
                    self.transcription_thread.start()

    def _stop_recording(self):
        """Internal method to stop recording and complete transcription."""
        print("\n🛑 Recording stopped, processing audio...")
        self.is_recording = False

        # Stop microphone input
        audio_file = self.recorder.stop_recording()
        if not audio_file:
            print("⚠️  No audio captured; skipping transcription.")
            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=2.0)
            return

        # Get recording duration
        try:
            data, samplerate = sf.read(audio_file)
            duration = len(data) / samplerate
        except:
            duration = 0

        # Check if recording was too short for streaming
        if duration < self.recorder.start_delay_seconds:
            print(f"⚡ Short recording ({duration:.1f}s) - processing entire clip...")

            # Stop any streaming that might have started
            self.is_transcribing = False
            if self.transcription_thread:
                self.transcription_thread.join(timeout=2.0)

            text = self._transcribe_full_recording(audio_file)
            self._handle_final_text(text)

        else:
            # Normal streaming mode - process buffered chunks
            # Signal transcription thread to finish processing queue
            self.is_transcribing = False

            # Wait for transcription thread to process ALL remaining chunks
            if self.transcription_thread:
                print("⏳ Processing remaining chunks...")
                self.transcription_thread.join(timeout=30.0)

            final_text = self.chunk_merger.get_result()
            if not final_text:
                print("⚠️  No chunks processed, transcribing whole file as fallback...")
                final_text = self._transcribe_full_recording(audio_file)

            # Finalize and copy to clipboard
            self.finalize_transcription(final_text)

    def on_release(self, key):
        """Handle key release events."""
        if self.is_shutting_down:
            return False

        # Track released keys
        try:
            if key in self.current_keys:
                self.current_keys.remove(key)
        except:
            pass

        # Check if hotkey is released
        hotkey_combo = self._check_hotkey_pressed()

        # Reset debounce when keys released (for toggle mode)
        if self.toggle_mode and not hotkey_combo:
            self.hotkey_pressed = False

        # Hold mode: stop recording when hotkey released
        if not self.toggle_mode:
            if self.hotkey_pressed and not hotkey_combo:
                self.hotkey_pressed = False

                if self.recorder.is_recording:
                    self._stop_recording()

    def run(self):
        """Start the streaming STT server."""
        print("=" * 60)
        print("Streaming STT Server - Real-time Voice to Text")
        print("=" * 60)
        print(f"Auto-paste: {'Enabled' if self.auto_paste else 'Disabled'}")
        print(f"Speed: {self.speed}x")
        print(f"Chunk size: {self.recorder.window_seconds}s (context window)")
        print(f"Slide interval: {self.recorder.slide_seconds}s")
        print(
            f"Overlap: {self.recorder.window_seconds - self.recorder.slide_seconds}s (for merging)"
        )
        print(f"Start delay: {self.recorder.start_delay_seconds}s")
        if self.toggle_mode:
            print(
                f"Hotkey: {self.hotkey} - press once to start, again to stop"
            )
        else:
            print(f"Hotkey: {self.hotkey} - hold to record")
        if self.output_file:
            print(f"Output file: {self.output_file} (streaming)")
        print("Exit: Ctrl+C")
        print("=" * 60)

        # Load model
        if not self.load_model():
            return

        # Start keyboard listener
        try:
            if self.toggle_mode:
                print(
                    f"\n✓ Ready! Press {self.hotkey} once to start recording."
                )
            else:
                print(f"\n✓ Ready! Hold {self.hotkey} to start recording.")
            print(
                f"  Streaming will start after {self.recorder.start_delay_seconds}s\n"
            )

            with keyboard.Listener(
                on_press=self.on_press, on_release=self.on_release
            ) as listener:
                listener.join()
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.recorder.cleanup()
            if self.output_stream:
                self.output_stream.close()
            if self.streaming_ui:
                self.streaming_ui.stop()
            print("✓ Cleaned up")
