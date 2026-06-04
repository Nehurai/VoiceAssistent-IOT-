import re
import time
import argparse
import serial
import pyttsx3
from serial.tools import list_ports

PORT = "COM4"      # default, can be overridden with --port
BAUD = 115200

# Initialize TTS engine with fallbacks for Windows systems where pyttsx3 may fail
engine = None
sapi = None
_use_win32_sapi = False
try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)   # speaking speed
except Exception:
    try:
        import win32com.client
        sapi = win32com.client.Dispatch("SAPI.SpVoice")
        _use_win32_sapi = True
    except Exception:
        sapi = None

def speak(text, enabled=True):
    if not enabled:
        print("(TTS disabled) Assistant:", text)
        return
    print("Assistant:", text)
    if engine is not None:
        try:
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            pass
    if _use_win32_sapi and sapi is not None:
        try:
            sapi.Speak(text)
            return
        except Exception:
            pass

LINE_RE = re.compile(
    r"Temp:\s*([0-9.+-]+)C\s+Hum:\s*([0-9.+-]+)%\s+Air:\s*(\d+)ppm\s+Dist:\s*([0-9.+-]+)cm\s+Fan:\s*(\d+)",
    re.IGNORECASE,
)

def parse_sensor_line(line):
    m = LINE_RE.search(line)
    if not m:
        return None
    return {
        "temp": float(m.group(1)),
        "hum": float(m.group(2)),
        "air": int(m.group(3)),
        "dist": float(m.group(4)),
        "fan": int(m.group(5)),
    }

def choose_port_interactive(ports):
    if not ports:
        print("No serial ports detected.")
        return None
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f" [{i}] {p.device} -> {getattr(p,'description','')}")
    choice = input("Pick port index or enter device name (e.g. COM3), or press Enter to cancel: ").strip()
    if choice == "":
        return None
    if choice.isdigit():
        idx = int(choice)
        if 0 <= idx < len(ports):
            return ports[idx].device
        print("Invalid index.")
        return None
    return choice

def open_serial_with_retry(initial_port, baud, timeout=0.2):
    port = initial_port
    ser = None
    while True:
        try:
            ser = serial.Serial(port, baud, timeout=timeout)
            print(f"Opened {port}")
            return ser
        except PermissionError as pe:
            print(f"Access denied opening {port!r}: {pe}")
            print("Close any program using the port (Serial Monitor, PuTTY, VSCode) or run terminal as Administrator.")
            print("Options: [r]etry, [s]elect another port, [q]uit")
            choice = input("Choice (r/s/q): ").strip().lower()
            if choice == "r":
                continue
            if choice == "s":
                ports = list(list_ports.comports())
                new = choose_port_interactive(ports)
                if new:
                    port = new
                    continue
                else:
                    print("No selection made.")
                    continue
            print("Exiting.")
            return None
        except Exception as e:
            print(f"Could not open port {port!r}: {e}")
            ports = list(list_ports.comports())
            if ports:
                print("Try selecting another available port.")
                new = choose_port_interactive(ports)
                if new:
                    port = new
                    continue
            return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=PORT, help="Serial port (e.g. COM3)")
    parser.add_argument("--no-audio", action="store_true", help="Disable TTS output")
    parser.add_argument("--air-high", type=int, default=650, help="High air ppm threshold (alert when exceeded)")
    parser.add_argument("--air-low", type=int, default=600, help="Low air ppm threshold to clear alert")
    args = parser.parse_args()

    print(f"\n🔗 Connecting to {args.port} ...")
    ser = open_serial_with_retry(args.port, BAUD, timeout=0.2)
    if ser is None:
        speak("Failed to open any serial port. Update PORT or close conflicting apps.", enabled=not args.no_audio)
        return

    last_fan = None
    last_air_alert = None  # None=unknown, False=normal, True=high
    last_print = 0

    try:
        while True:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue
            # lines may be prefixed "ESP → " in your output; remove it
            line = raw.split("ESP →")[-1].strip()
            parsed = parse_sensor_line(line)
            # print raw line at most twice per second to avoid flooding
            now = time.time()
            if now - last_print > 0.4:
                print("ESP →", line)
                last_print = now

            if parsed is None:
                # couldn't parse; skip or optionally log
                continue

            # fan change announcement (only on transitions)
            if last_fan is None:
                last_fan = parsed["fan"]
            elif parsed["fan"] != last_fan:
                if parsed["fan"] == 1:
                    speak("Fan turned ON.", enabled=not args.no_audio)
                else:
                    speak("Fan turned OFF.", enabled=not args.no_audio)
                last_fan = parsed["fan"]

            # air quality alerts with hysteresis
            air = parsed["air"]
            if last_air_alert is None:
                last_air_alert = air > args.air_high
                if last_air_alert:
                    speak(f"Air is poor ({air} ppm). Purifier running.", enabled=not args.no_audio)
            else:
                if air > args.air_high and not last_air_alert:
                    speak(f"⚠ Air quality is bad: {air} ppm. Purifier started.", enabled=not args.no_audio)
                    last_air_alert = True
                elif air < args.air_low and last_air_alert:
                    speak(f"😊 Air is clean again: {air} ppm. Turning off purifier.", enabled=not args.no_audio)
                    last_air_alert = False

            # small sleep to avoid busy loop if device floods data
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nExiting (KeyboardInterrupt).")
    finally:
        try:
            if ser and ser.is_open:
                ser.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()