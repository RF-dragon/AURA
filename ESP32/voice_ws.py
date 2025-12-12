# voice_ws.py
import socket
import json
import _thread
import time

def start_server(on_message_callback, port=80):

    def server_thread():
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

                data = conn.recv(2048)
                if not data:
                    conn.close()
                    continue

                response_text = "OK"     # default response

                try:
                    msg = json.loads(data.decode())
                    print("📝 Voice JSON:", msg)

                    # process incoming json
                    on_message_callback(msg)

                    # respond with parsed mode
                    mode = msg.get("mode", "unknown")
                    response_text = f"received:{mode}"

                except Exception as e:
                    print("❌ JSON parse error:", e)
                    response_text = "error"

                # ----------------------------
                # SEND RESPONSE BACK TO GRADIO
                # ----------------------------
                try:
                    conn.send(response_text.encode())
                except Exception as e:
                    print("⚠️ Error sending response:", e)

                conn.close()

            except Exception as e:
                print("⚠️ Listener error:", e)
                time.sleep(0.1)

    _thread.start_new_thread(server_thread, ())
    print("🎧 Voice listener thread started")

