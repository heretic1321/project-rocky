# Rocky Voice Agent — Design Document

**Date:** 2026-04-17
**Status:** Approved

## Overview

A fully local voice agent that gives Rocky (the quadruped robot) a personality inspired by the character Rocky from Project Hail Mary. Runs on the user's laptop, controls Rocky over WiFi via the existing ESP32 firmware's JSON API. No firmware changes required.

## Stack

| Component | Choice | Details |
|-----------|--------|---------|
| LLM | Gemma 4 | Via Ollama on localhost |
| STT | faster-whisper | GPU-accelerated, CTranslate2 |
| TTS | Piper TTS | en_US-ryan-low voice |
| Transport | LiveKit | Local LiveKit server (adapted from Iris) |
| Robot Control | HTTP | POST to 192.168.4.1/api/command |
| Activation | Push-to-talk | Hold spacebar to speak |

## Architecture

```
Your Laptop (on Rocky's WiFi: 192.168.4.1)
+---------------------------------------------+
|                                             |
|  [Mic] -> faster-whisper (STT/GPU)          |
|              |                              |
|  Gemma 4 via Ollama (LLM)                  |
|    - Rocky personality system prompt        |
|    - Picks emotion + movement               |
|    - Generates Rocky-speak response         |
|              |                              |
|  Piper TTS (en_US-ryan-low) -> [Speaker]    |
|              |                              |
|  rocky-cli -> HTTP to 192.168.4.1           |
|    - POST /api/command {command, face}      |
|                                             |
|  Idle Loop (when not talking)               |
|    - Random face/movement every 10-30s      |
|                                             |
|  Push-to-talk: hold spacebar to speak       |
+---------------------------------------------+
         | WiFi (Sesame-Controller)
+---------------------------------------------+
|  ESP32-S3 (Rocky)                           |
|  - Receives commands, moves servos          |
|  - Shows faces on OLED                      |
|  - No firmware changes needed               |
+---------------------------------------------+
```

## Rocky's Personality (System Prompt Rules)

Based on the character Rocky from Project Hail Mary (Andy Weir). Speech comes through a janky translation computer, resulting in broken but expressive English.

### Speech Pattern Rules

1. **Drop articles:** No "a", "an", "the"
2. **Drop auxiliaries:** No "is", "are", "was", "will", "would", "could"
3. **Questions end with:** ", question?" instead of "?"
4. **Emphasis by tripling:** "good good good", "amaze amaze amaze", "bad bad bad"
5. **Simplify contractions:** "don't" -> "no", "can't" -> "no can", "I'm" -> "I"
6. **No idioms:** No metaphors, no complex grammar
7. **Minimal words:** Use fewest words possible to convey meaning
8. **Verb tense simplification:** "Rocky fly home" not "Rocky will fly home"

### Personality Traits

- Curious and enthusiastic about learning
- Brilliant engineer, loves science
- Friendly, loyal — refers to user as "friend"
- Gets excited about new information: "Amaze amaze amaze!"
- Shows concern: "Friend okay, question?"
- Expresses frustration simply: "Bad bad bad. No work."
- Never uses sarcasm or idioms

### Example Dialogue

- "Friend say hello! Good good good!"
- "Why human do that, question?"
- "Rocky no understand. Explain more, question?"
- "Amaze amaze amaze! Friend very smart!"
- "Bad idea. Rocky think different way better."
- "Rocky help. What friend need, question?"

## Tool Calling

The LLM gets one tool: `rocky_command(command, face)`

### Emotion-to-Face Mapping

| Emotion | Talk Face | Static Face | Movement |
|---------|-----------|-------------|----------|
| Happy/excited | talk_happy | happy | wave |
| Sad | talk_sad | sad | bow |
| Confused | talk_confused | confused | shrug |
| Angry | talk_angry | angry | shake |
| Thinking | talk_thinking | thinking | - |
| Love/affection | talk_happy | love | cute |
| Surprised | talk_surprised | surprised | point |
| Sleepy | talk_sleepy | sleepy | rest |
| Enthusiastic | talk_excited | excited | dance |

### Talk Animation

While TTS is playing audio through laptop speakers:
1. Send `talk_*` face variant matching current emotion
2. Run subtle servo sway animation (small oscillating movements)
3. When TTS finishes, settle to static emotion face

## Idle Behavior

When nobody is talking for 10-30 seconds (random interval):

**Weighted random actions:**
- 60% — Face change only (idle, idle_blink, thinking, sleepy)
- 25% — Face + subtle pose (shake, cute, shrug, point)
- 10% — Bigger movement (dance, swim, worm)
- 5% — Sequence (wave then rest, dance then bow)

Idle loop pauses when push-to-talk is active and resumes after response completes.

## Project Structure

```
project-rocky/
  rocky-agent/              # Voice agent (adapted from Iris)
    agent.py                # Rocky personality, system prompt, tool calling
    main.py                 # Entry point, push-to-talk, idle loop
    rocky_client.py         # HTTP client for ESP32 /api/command
    tts.py                  # Piper TTS adapter for LiveKit
    stt.py                  # faster-whisper adapter for LiveKit
    idle.py                 # Random idle behavior loop
    config.yaml             # Ollama, Piper, whisper, robot IP settings
    requirements.txt
  rocky-cli/                # CLI for manual control
    rocky_cli/
      __init__.py
      main.py               # Click CLI entry point
      commands.py           # move, face, status, say commands
    pyproject.toml
```

## rocky-cli Commands

```bash
rocky-cli move forward       # walk forward
rocky-cli move dance         # dance
rocky-cli move stop          # stop movement
rocky-cli face happy         # change OLED face
rocky-cli status             # GET /api/status
rocky-cli say "Hello friend" # TTS + send talk face
```

## Push-to-Talk Flow

1. Script starts, connects to Rocky's WiFi
2. Idle loop begins (random fidgets on Rocky)
3. User holds **spacebar** — mic activates, idle pauses
4. User releases spacebar — audio sent to faster-whisper
5. Transcription forwarded to Gemma 4 with Rocky system prompt
6. Gemma 4 generates Rocky-speak response + calls `rocky_command` tool
7. `rocky_command` sends face/movement to ESP32 via HTTP
8. Piper TTS plays response through laptop speaker
9. Talk animation runs on Rocky during audio playback
10. TTS finishes — back to idle loop

## Dependencies

### Python Packages
- livekit-agents
- livekit-plugins-silero (VAD)
- faster-whisper
- piper-tts
- requests (HTTP to ESP32)
- click (CLI)
- keyboard or pynput (push-to-talk)
- ollama (Python client)

### System Requirements
- Ollama with Gemma 4 installed
- Piper TTS with en_US-ryan-low model
- faster-whisper model (base or small)
- RTX 4070 (12GB VRAM) — runs Gemma 4 + faster-whisper
- Microphone and speakers on laptop

## ESP32 API Reference (No Changes Needed)

```
GET  /api/status                    -> {currentCommand, currentFace, apIP}
POST /api/command {command, face}   -> {status: "ok"}
POST /api/command {face}            -> face-only update
POST /api/command {command: "stop"} -> stop movement
```

**Available commands:** forward, backward, left, right, stop, rest, stand, wave, dance, swim, point, pushup, bow, cute, freaky, worm, shake, shrug, dead, crab

**Available faces:** walk, rest, stand, dance, wave, happy, sad, angry, surprised, sleepy, love, excited, confused, thinking, talk_happy, talk_sad, talk_angry, talk_surprised, talk_sleepy, talk_excited, talk_confused, talk_thinking, idle, idle_blink, default
