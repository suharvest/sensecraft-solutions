## What This Solution Does

This solution turns your LeKiwi robot into a voice-controlled companion. Speak natural commands like "move forward" or "turn left" — the robot understands, replies with a voice confirmation, and moves. No remote, no phone app, no keyboard. Just talk.

Everything runs on a Raspberry Pi — it listens for your voice, understands what you want, decides what to do, and talks back through speakers. A XIAO ESP32S3 controls the motors that drive the wheels. The guided deployment walks you through firmware flashing, servo ID setup, and the voice container.

## Core Benefits

- **Hands-free control** — Say "Hey Jarvis" and give a command. The robot listens, understands, and moves
- **Natural language** — No memorizing keybindings. Just speak what you want — "go forward", "slide left", "keep turning"
- **Voice replies** — The robot talks back. You'll hear confirmation and status through speakers
- **Omnidirectional movement** — Kiwi-drive lets the robot move forward, backward, strafe, and rotate seamlessly

## Use Cases

| Scenario | Description |
|----------|-------------|
| STEM education | Teach robotics, AI, and voice technology with a hands-on project students can literally talk to |
| Robot prototyping | Build a voice-controlled platform as a base for delivery robots, inspection bots, or companion robots |
| Interactive demos | Showcase AI integration at events — visitors can talk to the robot and see it respond |
| Accessibility research | Explore hands-free robot control for assistive technology applications |
| Home automation | Extend with sensors and additional commands to create a voice-controlled home robot |

## What You Need

### Hardware

| Part | Purpose |
|------|---------|
| LeKiwi Kit | 3-wheeled Kiwi-drive chassis with 3× STS3215 smart servos |
| XIAO ESP32S3 | Motor controller — receives serial commands from Raspberry Pi |
| Raspberry Pi 5 | Voice AI brain — runs the full voice pipeline |
| reSpeaker Flex XVF3800 | 4-microphone array for far-field voice capture |
| Speaker | Audio output for the robot's voice replies |
| USB cables | Pi ↔ XIAO, Pi ↔ reSpeaker, Pi ↔ power |

### Software & Accounts

- **Docker** on the Raspberry Pi
- **Groq API key** (free tier — sign up at [console.groq.com](https://console.groq.com/))

## Usage Notes

- **Hardware assembly is required** — physically build the LeKiwi chassis first; servo IDs are configured through the XIAO in Steps 2 and 3
- **Groq free tier is enough** — the free API quota handles casual use with no issues
- **Internet required** — voice recognition and LLM run on Groq's cloud, so the Pi needs internet
- **Speakers needed** — the robot talks back, so audio output is essential for the full experience
- **Servo power** — the STS3215 servos need external power (not just USB)
