#!/usr/bin/env python3
"""
Dasung Paperlike 253 – Linux Driver

Unofficial Linux driver for the Dasung Paperlike 253 E-Ink monitor.
Reverse-engineered from USB captures of the official Paperlike client.

Author:  Denis Sandmann <https://denissandmann.de>
License: MIT
"""
import serial
import time
import sys
import threading

KEEPALIVE_CMD = b"5FF52001000000000000A0FA"
KEEPALIVE_INTERVAL = 4  # Sekunden (Monitor-Timeout ist ~5s)

def send(ser, cmd, label="", wait=0.15):
    print(f"  → {cmd.decode()}  {label}")
    ser.write(cmd)
    time.sleep(wait)
    resp = ser.read_until(b"A0FA", size=64)
    if resp:
        s = resp.decode('ascii', errors='replace').strip()
        print(f"  ← {s}")
        return s
    return ""

def keepalive_loop(ser, stop_event):
    """Sendet alle 4 Sekunden den Keepalive-Befehl."""
    while not stop_event.is_set():
        time.sleep(KEEPALIVE_INTERVAL)
        if stop_event.is_set():
            break
        try:
            ser.write(KEEPALIVE_CMD)
            resp = ser.read_until(b"A0FA", size=64)
            ts = time.strftime("%H:%M:%S")
            if resp:
                s = resp.decode('ascii', errors='replace').strip()
                print(f"  [{ts}] keepalive → ← {s}")
            else:
                print(f"  [{ts}] keepalive → (keine Antwort)")
        except Exception as e:
            print(f"  Keepalive Fehler: {e}")
            break

def init_monitor(port='/dev/ttyUSB0', baud=115200, timeout=15):
    print(f"Opening {port} at {baud} baud...")

    ser = serial.Serial(port, baud, timeout=2,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE)
    try:
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Phase 0: RTS toggle
        print("\n[Phase 0] RTS toggle...")
        ser.rts = True
        time.sleep(0.1)
        ser.rts = False
        time.sleep(0.2)

        # Phase 1: Register auslesen
        print("\n[Phase 1] Querying registers...")
        send(ser, b"5FF50A10000000000000A0FA", "(firmware)")
        send(ser, b"5FF50A01000000000000A0FA", "(kontrast)")
        send(ser, b"5FF50A02000000000000A0FA", "(mode)")
        send(ser, b"5FF50A12000000000000A0FA", "(reg12)")
        send(ser, b"5FF50A13000000000000A0FA", "(reg13)")

        # Phase 2: Warten auf Ready-Signal
        print(f"\n[Phase 2] Warte auf Ready-Signal (bis {timeout}s)...")
        deadline = time.time() + timeout
        found = False
        while time.time() < deadline:
            data = ser.read_until(b"A0FA", size=64)
            if data:
                s = data.decode('ascii', errors='replace').strip()
                print(f"  ← {s}")
                if "5FF5F520" in s:
                    print("  ✓ Monitor bereit!")
                    found = True
                    break
            time.sleep(0.05)

        if not found:
            print(f"  ⚠ Kein Ready-Signal, mache trotzdem weiter...")

        # Phase 3: Display aktivieren
        print("\n[Phase 3] Display aktivieren...")
        send(ser, b"5FF52001000000000000A0FA", "(Display ON #1)", wait=0.2)
        send(ser, b"5FF50300000000000000A0FA", "(query reg03)", wait=0.2)
        send(ser, b"5FF52001000000000000A0FA", "(Display ON #2)", wait=0.3)
        send(ser, b"5FF52001000000000000A0FA", "(Display ON #3)", wait=0.3)

        # Phase 4: Keepalive-Loop starten
        print(f"\n[Phase 4] Keepalive aktiv (alle {KEEPALIVE_INTERVAL}s)")
        print("          Drücke Strg+C zum Beenden\n")

        stop_event = threading.Event()
        ka_thread = threading.Thread(target=keepalive_loop, args=(ser, stop_event), daemon=True)
        ka_thread.start()

        # Warten bis Strg+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStrg+C - Beende...")
            stop_event.set()
            ka_thread.join(timeout=2)

    finally:
        ser.close()
        print("Verbindung geschlossen.")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    init_monitor(port, baud, timeout)
