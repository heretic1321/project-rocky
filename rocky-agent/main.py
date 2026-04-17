"""Rocky voice agent — push-to-talk entry point.

Hold spacebar to talk to Rocky. Release to send.
Rocky responds with voice (Piper TTS) and robot movements/faces.
When idle, Rocky fidgets randomly.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from config import load_config
from rocky_client import RockyClient
from agent import RockyAgent, TALK_TO_STATIC
from idle import IdleLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("rocky.main")

# Piper TTS — lazy loaded
_piper_voice = None


def _get_piper_voice(model_name: str):
    global _piper_voice
    if _piper_voice is None:
        from piper import PiperVoice
        # Download model if not present
        model_dir = Path(__file__).parent / "models"
        model_dir.mkdir(exist_ok=True)
        model_path = model_dir / f"{model_name}.onnx"
        if not model_path.exists():
            logger.info("Downloading Piper model: %s", model_name)
            import subprocess
            subprocess.run([
                "piper", "--download-dir", str(model_dir),
                "--model", model_name,
                "--update-voices",
                "--sentence_silence", "0",
                "--output_file", "/dev/null",
            ], input="test", capture_output=True, text=True)
            # Find the downloaded model
            found = list(model_dir.glob(f"*{model_name}*.onnx"))
            if found:
                model_path = found[0]
        _piper_voice = PiperVoice.load(str(model_path))
    return _piper_voice


def speak(text: str, cfg: dict):
    """Synthesize and play speech using Piper TTS."""
    tts_cfg = cfg.get("tts", {})
    model_name = tts_cfg.get("model", "en_US-ryan-low")
    voice = _get_piper_voice(model_name)

    audio_chunks = []
    for chunk in voice.synthesize(text):
        audio_chunks.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))

    if not audio_chunks:
        return

    audio = np.concatenate(audio_chunks)
    audio_f32 = audio.astype(np.float32) / 32768.0

    sample_rate = tts_cfg.get("sample_rate", 22050)
    output_dev = cfg.get("audio", {}).get("output_device", "default")
    if output_dev == "default":
        output_dev = None

    sd.play(audio_f32, sample_rate, device=output_dev)
    sd.wait()


# faster-whisper STT — lazy loaded
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        cfg = load_config()
        stt_cfg = cfg.get("stt", {})
        _whisper_model = WhisperModel(
            stt_cfg.get("model", "base.en"),
            device=stt_cfg.get("device", "cuda"),
            compute_type=stt_cfg.get("compute_type", "float16"),
        )
    return _whisper_model


def transcribe(audio_f32: np.ndarray, language: str = "en") -> str:
    """Transcribe audio using faster-whisper."""
    model = _get_whisper()
    segments, _ = model.transcribe(audio_f32, beam_size=1, language=language, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments)


class PushToTalk:
    """Records audio while spacebar is held."""

    def __init__(self, sample_rate: int = 16000, device=None):
        self._sr = sample_rate
        self._device = device
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stream: sd.InputStream | None = None

    def start_recording(self):
        self._frames.clear()
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self._sr,
            channels=1,
            dtype="float32",
            device=self._device,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop_recording(self) -> np.ndarray:
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._frames)

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._frames.append(indata[:, 0].copy())


async def main():
    cfg = load_config()

    robot_url = cfg.get("robot", {}).get("url", "http://192.168.4.1")
    client = RockyClient(robot_url)

    # Check if Rocky is reachable
    status = client.status()
    if status:
        logger.info("Connected to Rocky at %s", robot_url)
    else:
        logger.warning("Cannot reach Rocky at %s — continuing anyway (commands will fail)", robot_url)

    agent = RockyAgent(
        client=client,
        ollama_model=cfg.get("llm", {}).get("model", "gemma4:e4b"),
        ollama_url=cfg.get("llm", {}).get("base_url", "http://localhost:11434"),
    )

    idle_cfg = cfg.get("idle", {})
    idle_loop = IdleLoop(
        client,
        min_interval=idle_cfg.get("min_interval", 10),
        max_interval=idle_cfg.get("max_interval", 30),
    )

    input_dev = cfg.get("audio", {}).get("input_device", "default")
    if input_dev == "default":
        input_dev = None

    ptt = PushToTalk(sample_rate=16000, device=input_dev)

    # Pre-load models in background
    logger.info("Loading models...")
    await asyncio.to_thread(_get_whisper)
    logger.info("STT ready (faster-whisper)")
    await asyncio.to_thread(lambda: _get_piper_voice(cfg.get("tts", {}).get("model", "en_US-ryan-low")))
    logger.info("TTS ready (Piper)")

    # Verify Ollama is running
    import requests
    try:
        r = requests.get(f"{cfg.get('llm', {}).get('base_url', 'http://localhost:11434')}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        target = cfg.get("llm", {}).get("model", "gemma4:e4b")
        if target in models:
            logger.info("LLM ready (Ollama: %s)", target)
        else:
            logger.warning("Model %s not found in Ollama. Available: %s", target, models)
    except requests.RequestException:
        logger.error("Cannot reach Ollama. Is it running?")
        sys.exit(1)

    # Start idle behavior
    idle_loop.start()

    print("\n" + "=" * 50)
    print("  ROCKY VOICE AGENT")
    print("  Hold SPACEBAR to talk, release to send")
    print("  Press 'q' to quit")
    print("=" * 50 + "\n")

    # Send initial greeting face
    client.send(face="happy")

    # Keyboard listener runs in a thread
    space_pressed = threading.Event()
    space_released = threading.Event()
    quit_flag = threading.Event()

    def _keyboard_listener():
        try:
            from pynput import keyboard

            def on_press(key):
                if key == keyboard.Key.space and not space_pressed.is_set():
                    space_pressed.set()
                    space_released.clear()

            def on_release(key):
                if key == keyboard.Key.space:
                    space_released.set()
                    space_pressed.clear()
                elif hasattr(key, 'char') and key.char == 'q':
                    quit_flag.set()
                    return False

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except ImportError:
            logger.error("pynput not installed. Run: pip install pynput")
            quit_flag.set()

    kb_thread = threading.Thread(target=_keyboard_listener, daemon=True)
    kb_thread.start()

    try:
        while not quit_flag.is_set():
            # Wait for spacebar press
            while not space_pressed.is_set() and not quit_flag.is_set():
                await asyncio.sleep(0.05)

            if quit_flag.is_set():
                break

            # Spacebar pressed — start recording
            idle_loop.pause()
            client.send(face="thinking")
            print("[Recording... release spacebar to send]")
            ptt.start_recording()

            # Wait for release
            while not space_released.is_set() and not quit_flag.is_set():
                await asyncio.sleep(0.05)

            if quit_flag.is_set():
                break

            # Stop recording and transcribe
            audio = ptt.stop_recording()
            if len(audio) < 1600:  # Less than 0.1s of audio
                print("[Too short, skipped]")
                idle_loop.resume()
                continue

            print("[Transcribing...]")
            text = await asyncio.to_thread(transcribe, audio)
            if not text.strip():
                print("[No speech detected]")
                idle_loop.resume()
                continue

            print(f"You: {text}")

            # Get Rocky's response
            print("[Rocky is thinking...]")
            response_text, static_face = await asyncio.to_thread(agent.process, text)

            if response_text:
                print(f"Rocky: {response_text}")
                # Speak through laptop speakers
                await asyncio.to_thread(speak, response_text, cfg)

                # After TTS finishes, switch to static face
                if static_face:
                    client.send(face=static_face)

            # Resume idle
            idle_loop.resume()

    except KeyboardInterrupt:
        pass
    finally:
        idle_loop.stop()
        client.send(face="sleepy", command="rest")
        print("\nRocky go sleep. Bye bye, Friend!")


if __name__ == "__main__":
    asyncio.run(main())
