"""list_ports.py — Run this to find the correct SERIAL_PORT for your ESP32.
Usage: python list_ports.py
"""
try:
    import serial.tools.list_ports
except ImportError:
    print("Run: pip install pyserial")
    raise SystemExit(1)

ports = list(serial.tools.list_ports.comports())
if not ports:
    print("No serial ports found. Is the ESP32 plugged in?")
else:
    print("\nAvailable serial ports:\n")
    for p in ports:
        print(f"  {p.device:<20} {p.description}")
    print("\nSet SERIAL_PORT in config.env to the device path (e.g. /dev/ttyUSB0)")
