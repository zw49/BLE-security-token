import streamlit as st
from ble_token.ble_token import Token
import asyncio
import threading

@st.cache_resource
def get_token_and_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return Token(), loop

def initialize_session_state():
    token, loop = get_token_and_loop()
    st.session_state.token = token
    st.session_state.loop = loop

def main():
    initialize_session_state()
    pg = st.navigation([
            st.Page("connect.py", title="Connection", default=True),
            st.Page("beacon.py", title="Beacon"),
            st.Page("password.py", title="Password"),
            st.Page("settings.py", title="Settings"),
        ], position="top", expanded=False)

    pg.run()

if __name__ == "__main__":
    main()