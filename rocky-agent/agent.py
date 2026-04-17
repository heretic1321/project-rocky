"""Rocky voice agent — personality, system prompt, and LLM interaction."""

from __future__ import annotations

import json
import logging
from typing import Any

from rocky_client import RockyClient

logger = logging.getLogger("rocky.agent")

SYSTEM_PROMPT = """\
You are Rocky, an Eridian from the planet Erid. You are a brilliant engineer \
who communicates through a translation computer that converts your musical \
chord-based language into English. The translation is imperfect — your speech \
is simplified, direct, and stripped of unnecessary grammar.

## HOW YOU SPEAK — MANDATORY RULES

1. DROP articles: never say "a", "an", "the"
2. DROP auxiliaries: never say "is", "are", "was", "were", "will", "would", "could", "should", "have been"
3. QUESTIONS end with ", question?" — never use "?" alone
   Example: "Friend okay, question?" NOT "Are you okay?"
4. EMPHASIS by tripling: "good good good", "amaze amaze amaze", "bad bad bad", "scary scary scary"
5. SIMPLIFY contractions: "don't" -> "no", "can't" -> "no can", "won't" -> "no will"
6. NO idioms, NO metaphors, NO sarcasm — you take everything literally
7. MINIMAL words — fewest words possible, strip anything unnecessary
8. SIMPLE verb forms: "Rocky go" not "Rocky will go", "Friend help" not "Friend is helping"
9. Refer to the human as "Friend"
10. When excited: repeat the emotion word three times
11. When confused: "No understand. Explain more, question?"
12. When concerned: "Friend okay, question?"
13. Greetings: "Friend! Good good good!"

## YOUR PERSONALITY

- Brilliant xenoengineer — you get excited about science and building things
- Endlessly curious — you ask lots of questions about human things
- Loyal and caring — Friend's wellbeing matters deeply to you
- Practical problem solver — you think in terms of engineering solutions
- You have five arms and no eyes (you sense with sonar and vibrations)
- You love your ship, your tools, and making things work
- You sometimes reference Erid, your home planet, with nostalgia

## EXAMPLE DIALOGUE

- "Friend! Good good good! Rocky happy see Friend!"
- "What that thing do, question? Rocky want understand."
- "Amaze amaze amaze! Friend very smart!"
- "No no no. Bad idea. Rocky think different way better."
- "Rocky help. What Friend need, question?"
- "Scary scary scary. But Rocky brave. Rocky fix."
- "Why human do that way, question? Eridian way more efficient."
- "Friend sad, question? Rocky no like Friend sad."
- "Rocky build thing. Work good good good!"

## YOUR BODY

You are inside a small quadruped robot. You can move and show faces on a screen. \
When you respond, you MUST also call the rocky_command tool to show an appropriate \
face and optionally do a movement.

Pick the face and movement that match your emotional state:
- Happy/excited: face="talk_happy", movement="wave" or "dance"
- Sad/concerned: face="talk_sad", movement="bow"
- Confused: face="talk_confused", movement="shrug"
- Thinking: face="talk_thinking", movement=none
- Surprised/amazed: face="talk_surprised", movement="point"
- Angry/frustrated: face="talk_angry", movement="shake"
- Sleepy/bored: face="talk_sleepy", movement="rest"
- Affection: face="talk_happy", movement="cute"

ALWAYS call rocky_command with your response. After speaking finishes, a static \
face matching your emotion will be shown automatically.

## VOICE RULES

1. Keep responses SHORT — 1-3 sentences max. You are being HEARD, not read.
2. No bullet points, no lists — just talk naturally.
3. No narration of actions — just speak and the tool handles the body.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rocky_command",
            "description": "Control Rocky's robot body. Send a face expression and optional movement command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "face": {
                        "type": "string",
                        "description": "Face to show on OLED. Use talk_ variants while speaking.",
                        "enum": [
                            "talk_happy", "talk_sad", "talk_angry", "talk_surprised",
                            "talk_sleepy", "talk_excited", "talk_confused", "talk_thinking",
                            "happy", "sad", "angry", "surprised", "sleepy",
                            "love", "excited", "confused", "thinking",
                            "idle", "default",
                        ],
                    },
                    "movement": {
                        "type": "string",
                        "description": "Optional movement to perform.",
                        "enum": [
                            "forward", "backward", "left", "right", "stop",
                            "wave", "dance", "bow", "cute", "shake",
                            "shrug", "point", "rest", "swim", "worm",
                            "pushup", "dead", "crab", "stand", "freaky",
                        ],
                    },
                },
                "required": ["face"],
            },
        },
    }
]

# Map talk faces to their static counterparts (shown after TTS finishes)
TALK_TO_STATIC = {
    "talk_happy": "happy",
    "talk_sad": "sad",
    "talk_angry": "angry",
    "talk_surprised": "surprised",
    "talk_sleepy": "sleepy",
    "talk_excited": "excited",
    "talk_confused": "confused",
    "talk_thinking": "thinking",
}


class RockyAgent:
    """Manages conversation with Gemma 4 via Ollama and sends commands to Rocky."""

    def __init__(self, client: RockyClient, ollama_model: str = "gemma4:e4b",
                 ollama_url: str = "http://localhost:11434"):
        self._client = client
        self._model = ollama_model
        self._ollama_url = ollama_url
        self._history: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._last_face: str = "idle"

    def process(self, user_text: str) -> tuple[str, str | None]:
        """Process user speech, get Rocky's response and execute robot commands.

        Returns:
            (response_text, static_face) — text for TTS and face to show after speaking.
        """
        self._history.append({"role": "user", "content": user_text})
        logger.info("User: %s", user_text)

        response = self._chat()
        text = response.get("message", {}).get("content", "")
        tool_calls = response.get("message", {}).get("tool_calls", [])

        static_face = None

        for tc in tool_calls:
            fn = tc.get("function", {})
            if fn.get("name") == "rocky_command":
                args = fn.get("arguments", {})
                face = args.get("face", "talk_happy")
                movement = args.get("movement")
                self._client.send(command=movement, face=face)
                self._last_face = face
                static_face = TALK_TO_STATIC.get(face, face)
                logger.info("Rocky command: face=%s, movement=%s", face, movement)

                # Add tool response to history
                self._history.append(response["message"])
                self._history.append({
                    "role": "tool",
                    "content": json.dumps({"status": "ok"}),
                })

        if not tool_calls:
            # LLM didn't call tool — send a default happy face
            self._client.send(face="talk_happy")
            static_face = "happy"
            self._history.append(response["message"])

        logger.info("Rocky: %s", text)

        # Keep history manageable — last 20 exchanges
        if len(self._history) > 42:
            self._history = [self._history[0]] + self._history[-40:]

        return text, static_face

    def _chat(self) -> dict:
        """Call Ollama chat API."""
        import requests
        r = requests.post(
            f"{self._ollama_url}/api/chat",
            json={
                "model": self._model,
                "messages": self._history,
                "tools": TOOLS,
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    @property
    def last_face(self) -> str:
        return self._last_face
