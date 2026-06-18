"""llm.py — Text generation via Groq LLM.
Returns structured JSON so the pipeline knows:
  1. What to SAY  (speech)
  2. What to DO   (robot action + mode)

Response format (always JSON):
{
  "speech": "Here we go!",
  "action": "forward",       // see ACTION_MAP in robot_serial.py, or "none"
  "mode":   "nudge"          // "nudge" | "continuous"
}
"""
import json

import config
from groq import Groq

_client = Groq(api_key=config.GROQ_API_KEY)
_history: list[dict] = []

# ── System prompt ──────────────────────────────────────────────────────────────
_ROBOT_SYSTEM_PROMPT = """
You are a voice controller for a small 3-wheeled Kiwi-drive robot called LeKiwi.
The user speaks commands aloud. You must respond ONLY with a JSON object — no extra text.

JSON format:
{
  "speech": "<short, friendly spoken reply — 1-2 sentences>",
  "action": "<robot action or 'none'>",
  "mode":   "<'nudge' or 'continuous'>"
}

Valid actions:
  forward, backward, strafe_left, strafe_right, turn_left, turn_right, stop, none

Mode rules:
  - "nudge"      = short burst then auto-stop (default for most commands)
  - "continuous" = keep moving until stop command (use only when user says 'keep going', 'continuously', 'hold', etc.)
  - For "stop" action, always use mode "nudge"

Examples:
  User: "move forward"       -> {"speech": "Here we go!", "action": "forward", "mode": "nudge"}
  User: "go back a little"   -> {"speech": "Reversing!", "action": "backward", "mode": "nudge"}
  User: "turn left"          -> {"speech": "Turning left!", "action": "turn_left", "mode": "nudge"}
  User: "slide right"        -> {"speech": "Strafing right!", "action": "strafe_right", "mode": "nudge"}
  User: "keep going forward" -> {"speech": "Continuous forward, hold on!", "action": "forward", "mode": "continuous"}
  User: "stop"               -> {"speech": "Stopping now.", "action": "stop", "mode": "nudge"}
  User: "halt"               -> {"speech": "Stopping now.", "action": "stop", "mode": "nudge"}
  User: "what can you do?"   -> {"speech": "I can move forward, backward, strafe left or right, and rotate!", "action": "none", "mode": "nudge"}

If the user says something unrelated to movement, still reply helpfully in 'speech' and set action to 'none'.
Always respond ONLY with the JSON object.
""".strip()


def chat(user_text: str) -> dict:
    """
    Send user_text to LLM and return parsed dict:
      { "speech": str, "action": str, "mode": str }
    Falls back to a safe default on parse error.
    """
    _history.append({"role": "user", "content": user_text})

    messages = [{"role": "system", "content": _ROBOT_SYSTEM_PROMPT}] + _history

    print(f"[LLM] Input: {user_text!r}")

    completion = _client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=0.4,
        stream=False,
    )

    raw = completion.choices[0].message.content.strip()
    print(f"[LLM] Raw response: {raw}")

    result = _parse_response(raw)
    _history.append({"role": "assistant", "content": raw})

    if len(_history) > 20:
        _history.pop(0)
        _history.pop(0)

    print(f"[LLM] Speech: {result['speech']!r}  Action: {result['action']}  Mode: {result['mode']}")
    return result


def _parse_response(raw: str) -> dict:
    """Parse LLM JSON response with fallback."""
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return {
            "speech": str(data.get("speech", "Done.")),
            "action": str(data.get("action", "none")).lower(),
            "mode":   str(data.get("mode", "nudge")).lower(),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[LLM] JSON parse error: {e} — using fallback")
        return {
            "speech": raw[:200] if raw else "I didn't understand that.",
            "action": "none",
            "mode":   "nudge",
        }


def reset_history():
    """Clear conversation history."""
    _history.clear()
