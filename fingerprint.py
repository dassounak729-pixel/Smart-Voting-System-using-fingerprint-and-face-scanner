import sqlite3
import os
import time
 
# ── Same database as main.py ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "voting.db")
 
# ── Arduino serial object — shared from main.py ───────────────────────────────
# main.py sets this after connecting
arduino = None


class FingerprintSerialError(Exception):
    """Raised when fingerprint serial communication fails."""
 

def set_arduino(a):
    global arduino
    arduino = a
 
# ── Send command to Arduino ───────────────────────────────────────────────────
def send(msg):
    if not arduino or not arduino.is_open:
        raise FingerprintSerialError("Arduino not connected")
    try:
        arduino.write((msg + "\n").encode())
    except Exception as exc:
        raise FingerprintSerialError(f"Failed to send '{msg}'") from exc


def flush_input_buffer():
    """Discard buffered serial data so a new command reads fresh responses."""
    if not arduino or not arduino.is_open:
        return
    try:
        if hasattr(arduino, "reset_input_buffer"):
            arduino.reset_input_buffer()
            return
        while arduino.in_waiting:
            arduino.readline()
    except Exception as exc:
        raise FingerprintSerialError("Failed to clear serial input buffer") from exc
 
# ── Read a line from Arduino ──────────────────────────────────────────────────
def read_line(timeout=20):
    if not arduino or not arduino.is_open:
        return None
    start = time.time()
    while time.time() - start < timeout:
        try:
            if arduino.in_waiting:
                line = arduino.readline().decode(errors="ignore").strip()
                if line:
                    return line
        except Exception as exc:
            raise FingerprintSerialError("Lost communication with Arduino") from exc
        time.sleep(0.05)
    return None


def parse_prefixed_int(line, prefix):
    if not line.startswith(prefix):
        raise ValueError(f"Expected line starting with {prefix!r}, got {line!r}")
    value = line[len(prefix):].strip()
    if not value:
        raise ValueError(f"Missing value in line: {line!r}")
    return int(value)
 
# ── Enroll fingerprint — called during voter registration ─────────────────────
def enroll_fingerprint(on_status):
    """
    Sends ENROLL command to Arduino, waits for result.
    on_status(msg) is called with status updates for the UI.
    Returns the fingerprint ID (int) on success, or None on failure.
    """
    if not arduino or not arduino.is_open:
        on_status("⚠️  Arduino not connected — enter ID manually")
        return None
 
    try:
        flush_input_buffer()
        send("ENROLL")
    except FingerprintSerialError as exc:
        on_status(f"❌  {exc}")
        return None

    on_status("📡  Communicating with fingerprint sensor...")
 
    while True:
        try:
            line = read_line(timeout=30)
        except FingerprintSerialError as exc:
            on_status(f"❌  {exc}")
            return None

        if line is None:
            on_status("❌  Timeout — no response from Arduino")
            return None
 
        if line.startswith("ENROLL_ID:"):
            try:
                fp_id = parse_prefixed_int(line, "ENROLL_ID:")
            except ValueError:
                on_status(f"⚠️  Invalid sensor response: {line}")
                continue
            on_status(f"🆔  Assigned Fingerprint ID: {fp_id}")
 
        elif line == "PLACE_FINGER":
            on_status("👆  Place finger on sensor...")
 
        elif line == "REMOVE_FINGER":
            on_status("✋  Remove finger...")
 
        elif line == "PLACE_AGAIN":
            on_status("👆  Place the same finger again...")
 
        elif line.startswith("ENROLL_OK:"):
            try:
                fp_id = parse_prefixed_int(line, "ENROLL_OK:")
            except ValueError:
                on_status(f"⚠️  Invalid sensor response: {line}")
                continue
            on_status(f"✅  Fingerprint enrolled! ID: {fp_id}")
            return fp_id
 
        elif line.startswith("ENROLL_ERROR:"):
            reason = line[len("ENROLL_ERROR:"):].strip() or "Unknown error"
            on_status(f"❌  Enroll failed: {reason}")
            return None
 
# ── Verify fingerprint — called during voting ─────────────────────────────────
def verify_fingerprint(on_status):
    """
    Sends VERIFY command to Arduino, waits for fingerprint scan.
    on_status(msg) is called with status updates for the UI.
    Returns fingerprint ID (int) on success, or None on failure/not found.
    """
    if not arduino or not arduino.is_open:
        on_status("⚠️  Arduino not connected")
        return None
 
    try:
        flush_input_buffer()
        send("VERIFY")
    except FingerprintSerialError as exc:
        on_status(f"❌  {exc}")
        return None

    on_status("👆  Place finger on sensor...")
 
    while True:
        try:
            line = read_line(timeout=20)
        except FingerprintSerialError as exc:
            on_status(f"❌  {exc}")
            return None

        if line is None:
            on_status("❌  Timeout — no response from Arduino")
            return None
 
        if line == "PLACE_FINGER":
            on_status("👆  Place finger on sensor...")
 
        elif line.startswith("FP:"):
            try:
                fp_id = parse_prefixed_int(line, "FP:")
            except ValueError:
                on_status(f"⚠️  Invalid sensor response: {line}")
                continue
            on_status(f"✅  Fingerprint scanned! ID: {fp_id}")
            return fp_id
 
        elif line == "FP_NOTFOUND":
            on_status("❌  Fingerprint not recognised")
            return None
 
# ── Delete fingerprint from Arduino sensor ────────────────────────────────────
def delete_fingerprint(fp_id):
    if not arduino or not arduino.is_open:
        return False
    try:
        flush_input_buffer()
        send(f"DELETE:{fp_id}")
    except FingerprintSerialError:
        return False

    while True:
        try:
            line = read_line(timeout=5)
        except FingerprintSerialError:
            return False
        if line is None:
            return False
        if line.startswith("DELETE_OK"):
            return True
        if line.startswith("DELETE_ERROR"):
            return False
 
# ── Database functions ────────────────────────────────────────────────────────
def check_voter(fid):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM voters WHERE fingerprint_id=?", (fid,))
    user = cursor.fetchone()
    conn.close()
    return user
 
def mark_voted(fid):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE voters SET has_voted=1 WHERE fingerprint_id=?", (fid,))
    cursor.connection.commit()
    conn.close()
 
# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import serial
    try:
        a = serial.Serial("COM3", 9600, timeout=1)
        time.sleep(2)
        set_arduino(a)
        print("Arduino connected")
 
        choice = input("1=Enroll  2=Verify  3=Delete: ").strip()
        if choice == "1":
            enroll_fingerprint(print)
        elif choice == "2":
            fp_id = verify_fingerprint(print)
            if fp_id is not None:
                user = check_voter(fp_id)
                print(f"Voter: {user}")
        elif choice == "3":
            fid = int(input("Enter fingerprint ID to delete: "))
            print(delete_fingerprint(fid))
    except Exception as e:
        print(f"Error: {e}")
