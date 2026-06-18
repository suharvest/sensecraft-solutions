"""robot_serial.py — Serial command sender to ESP32 (LeKiwi controller).

Command map (matches Arduino sketch exactly):
  Nudge (single move + auto stop):
    'w' = Forward        's' = Backward
    'q' = Strafe Left    'e' = Strafe Right
    'a' = Turn Left      'd' = Turn Right

  Continuous (moves until stop sent):
    'W' = Forward        'S' = Backward
    'Q' = Strafe Left    'E' = Strafe Right
    'A' = Turn Left      'D' = Turn Right

  Control:
    'x' = Emergency Stop
    '+' / '-' = Increase / Decrease nudge duration
    '*' / '/' = Increase / Decrease nudge speed
"""
import time

import config
import serial
import serial.tools.list_ports

# ── Command table ─────────────────────────────────────────────────────────────
# Maps LLM action names → (nudge_char, continuous_char)
ACTION_MAP: dict[str, tuple[str, str]] = {
    "forward":       ("w", "W"),
    "backward":      ("s", "S"),
    "strafe_left":   ("q", "Q"),
    "strafe_right":  ("e", "E"),
    "turn_left":     ("a", "A"),
    "turn_right":    ("d", "D"),
    "stop":          ("x", "x"),
}


class RobotSerial:
    def __init__(self):
        self._port: serial.Serial | None = None
        self._connect()

    # ── connection ─────────────────────────────────────────────────────────────

    def _connect(self):
        port = self._resolve_port()
        if not port:
            print("[Robot] SERIAL_PORT not set — robot commands disabled")
            return
        try:
            self._port = serial.Serial(
                port=port,
                baudrate=config.SERIAL_BAUD,
                timeout=1,
            )
            time.sleep(2)           # ESP32 resets on serial open — wait for boot
            self._flush_boot_msg()
            print(f"[Robot] Connected on {port} @ {config.SERIAL_BAUD}")
        except serial.SerialException as e:
            print(f"[Robot] Could not open serial port: {e}")
            self._port = None

    def _resolve_port(self) -> str:
        configured = config.SERIAL_PORT
        if configured and configured.lower() != "auto":
            return configured

        ports = list(serial.tools.list_ports.comports())
        preferred = [
            port
            for port in ports
            if "espressif" in (port.manufacturer or "").lower()
            or "jtag" in (port.description or "").lower()
            or "serial debug" in (port.description or "").lower()
            or ((port.vid, port.pid) == (0x303A, 0x1001))
        ]
        candidates = preferred or [port for port in ports if port.device.startswith("/dev/ttyACM")]
        if not candidates:
            print("[Robot] No ESP32 serial port found")
            return ""
        port = sorted(candidates, key=lambda item: item.device)[0].device
        print(f"[Robot] Auto-selected serial port: {port}")
        return port

    def _flush_boot_msg(self):
        """Drain any boot messages the ESP32 sends on connect."""
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if self._port and self._port.in_waiting:
                line = self._port.readline().decode(errors="ignore").strip()
                if line:
                    print(f"[Robot][ESP32] {line}")
            else:
                time.sleep(0.05)

    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open

    # ── public API ─────────────────────────────────────────────────────────────

    def send_action(self, action: str, mode: str = "nudge") -> bool:
        """
        Send a named action to the robot.

        Args:
            action: one of the keys in ACTION_MAP  (e.g. "forward")
            mode:   "nudge" (auto-stops) or "continuous" (runs until stop)

        Returns:
            True if command was sent successfully.
        """
        if action == "none" or not action:
            print("[Robot] No action to send")
            return True

        entry = ACTION_MAP.get(action)
        if entry is None:
            print(f"[Robot] Unknown action: {action!r}")
            return False

        char = entry[0] if mode == "nudge" else entry[1]
        return self._send_char(char)

    def send_stop(self) -> bool:
        """Emergency stop."""
        return self._send_char("x")

    def adjust_nudge(self, duration_delta: int = 0, speed_delta: int = 0):
        """Adjust nudge duration (+/-) and speed (*  /) on the ESP32."""
        if duration_delta > 0:
            for _ in range(abs(duration_delta)):
                self._send_char("+")
        elif duration_delta < 0:
            for _ in range(abs(duration_delta)):
                self._send_char("-")

        if speed_delta > 0:
            for _ in range(abs(speed_delta)):
                self._send_char("*")
        elif speed_delta < 0:
            for _ in range(abs(speed_delta)):
                self._send_char("/")

    # ── private ────────────────────────────────────────────────────────────────

    def _send_char(self, char: str) -> bool:
        if not self.is_connected():
            print(f"[Robot] NOT connected — would have sent: {char!r}")
            return False
        try:
            self._port.write((char + "\n").encode())
            self._port.flush()
            print(f"[Robot] Sent command: {char!r}")
            # Read echo / confirmation from ESP32 (non-blocking, best effort)
            time.sleep(0.05)
            while self._port.in_waiting:
                line = self._port.readline().decode(errors="ignore").strip()
                if line:
                    print(f"[Robot][ESP32] {line}")
            return True
        except serial.SerialException as e:
            print(f"[Robot] Serial write error: {e}")
            self._port = None
            return False

    def close(self):
        if self._port and self._port.is_open:
            self.send_stop()
            self._port.close()
            print("[Robot] Serial port closed")


# Module-level singleton — imported by pipeline.py
_robot: RobotSerial | None = None


def get_robot() -> RobotSerial:
    global _robot
    if _robot is None:
        _robot = RobotSerial()
    return _robot
