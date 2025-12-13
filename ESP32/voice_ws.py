# voice_ws.py - Minimal TCP JSON listener for AURA voice commands
#
# Usage pattern:
# - main.py calls start_server(callback), which spawns a background thread.
# - A client connects and sends a single JSON blob (e.g., {"mode":"STUDY"}).
# - We invoke the callback with the parsed dict and reply with a small ACK string.

import socket
import json
import _thread
import time

def start_server(on_message_callback, port=80):
    """
    Start a background TCP server that accepts JSON messages.

    Args:
        on_message_callback: function(dict) -> None, called with parsed JSON.
        port: listening port (default 80).
    """

    def server_thread():
        # Bind on all interfaces so it works regardless of STA/AP IP.
        HOST = ""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port))
        s.listen(1)
        print("🔊 Voice command listener running on port", port)

        while True:
            try:
                conn, addr = s.accept()
                print("📶 Voice connection from:", addr)

                # Single-shot request model: read one payload then close.
                data = conn.recv(2048)
                if not data:
                    conn.close()
                    continue

                response_text = "OK"     # default response for non-JSON / errors

                try:
                    msg = json.loads(data.decode())
                    print("📝 Voice JSON:", msg)

                    # Delegate semantic handling to the caller (main.py/controller).
                    on_message_callback(msg)

                    # Small response that clients can use for confirmation/debug.
                    mode = msg.get("mode", "unknown")
                    response_text = f"received:{mode}"

                except Exception as e:
                    print("❌ JSON parse error:", e)
                    response_text = "error"

                try:
                    conn.send(response_text.encode())
                except Exception as e:
                    print("⚠️ Error sending response:", e)

                conn.close()

            except Exception as e:
                # Keep the listener resilient (e.g., transient socket errors).
                print("⚠️ Listener error:", e)
                time.sleep(0.1)

    _thread.start_new_thread(server_thread, ())
    print("🎧 Voice listener thread started")
