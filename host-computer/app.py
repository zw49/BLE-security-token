import streamlit as st
from ble_token.ble_token import Token
import asyncio
import threading

def _start_background_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop

def initialize_session_state():
    if "loop" not in st.session_state:
        st.session_state.loop = _start_background_loop()
    if "token" not in st.session_state:
        st.session_state.token = Token()




def main():
    initialize_session_state()
    pg = st.navigation([
            st.Page("beacon.py", title="Beacon"),
            st.Page("password.py", title="Password"),
        ])

    pg.run()

if __name__ == "__main__":
    main()