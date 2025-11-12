from flask import Flask, jsonify, send_from_directory
import serial
import serial.tools.list_ports
import threading
import time

app = Flask(__name__, static_folder='.', static_url_path='')

arduino = None
arduino_ready = False


def find_arduino_port():
    """Find Arduino COM port (works for official & CH340 clones)."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description:
            return port.device
    return None


def connect_arduino():
    """Attempt to connect to the Arduino."""
    global arduino
    port = find_arduino_port()
    if not port:
        print("❌ Arduino not found.")
        return False
    try:
        arduino = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)
        print(f"✅ Connected to Arduino at {port}")
        return True
    except Exception as e:
        print("❌ Serial connection failed:", e)
        return False


def monitor_arduino():
    """Continuously read serial messages and update LED status."""
    global arduino_ready
    while True:
        if arduino and arduino.is_open:
            try:
                line = arduino.readline().decode().strip().upper()
                if line == "GREEN":
                    arduino_ready = True
                    print("🟢 Arduino says GREEN — access allowed")
                elif line == "RED":
                    arduino_ready = False
                    print("🔴 Arduino says RED — access locked")
            except Exception as e:
                print("⚠️ Read error:", e)
        time.sleep(0.2)


@app.route('/')
def serve_index():
    """Serve the login page."""
    return send_from_directory('.', 'index.html')


@app.route('/authenticated.html')
def serve_authenticated():
    """Serve the authenticated (success) page."""
    return send_from_directory('.', 'authenticated.html')


@app.route('/status')
def status():
    """Frontend polls this every 2 seconds to check LED color."""
    return jsonify({"connected": arduino_ready})


@app.route('/login', methods=['POST'])
def login():
    """Allow login only if the Arduino is green."""
    if arduino_ready:
        return jsonify({"status": "success", "message": "🔓 Quantum login passed!"})
    else:
        return jsonify({"status": "fail", "message": "Arduino not ready (red phase)"})


if __name__ == '__main__':
    if connect_arduino():
        thread = threading.Thread(target=monitor_arduino, daemon=True)
        thread.start()
    # Disable Flask's auto-reloader to avoid serial port lock
    app.run(port=5000, debug=True, use_reloader=False)
