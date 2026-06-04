# Voice Assistant IOT

A simple Python voice assistant for monitoring sensor output from a serial-connected device (such as an ESP-based IoT board).

## Features
- Reads serial sensor data from a COM port
- Parses temperature, humidity, air quality, distance, and fan status
- Provides voice alerts using `pyttsx3` or Windows SAPI
- Supports air quality threshold alerts with hysteresis
- Interactive serial port selection if the default port is unavailable

## Requirements
- Python 3.8+
- `pyserial`
- `pyttsx3`
- On Windows, optional `pywin32` if `pyttsx3` initialization fails

## Installation
```powershell
python -m pip install pyserial pyttsx3
```

If you encounter TTS issues on Windows:
```powershell
python -m pip install pywin32
```

## Usage
```powershell
python voice_assistant.py --port COM4
```

Optional arguments:
- `--no-audio` : disable text-to-speech output
- `--air-high` : set the high air quality threshold (default `650`)
- `--air-low` : set the low air quality clear threshold (default `600`)

## Notes
- Update the default `PORT` in `voice_assistant.py` or pass `--port` to match your serial device.
- The script prints live sensor lines and announces state changes for fan and air quality.
