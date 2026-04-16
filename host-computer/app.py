import asyncio
import threading
import time
import streamlit as st
from ble_token import Token
import json
import base64



def _start_background_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop


if "loop" not in st.session_state:
    st.session_state.loop = _start_background_loop()
if "token" not in st.session_state:
    st.session_state.token = Token()
if "nonce_task" not in st.session_state:
    st.session_state.nonce_task = None

token = st.session_state.token
loop = st.session_state.loop


async def _nonce_loop():
    while token.is_connected:
        await token.send_nonce()
        await asyncio.sleep(10)


async def _connect_to_token():
    token.get_public_key()
    token.should_run_commands = False
    await token.connect()


def connect_to_token():
    with st.spinner("Connecting to token..."):
        asyncio.run_coroutine_threadsafe(_connect_to_token(), loop).result()
    # if token.is_connected and st.session_state.nonce_task is None:
    #     st.session_state.nonce_task = asyncio.run_coroutine_threadsafe(
    #         _nonce_loop(), loop
    #     )

def authenticate_with_token():
    if not token.is_connected:
        st.warning("Please connect to the token first.")
        return
    with st.spinner("Authenticating with token..."):
        asyncio.run_coroutine_threadsafe(token.send_nonce(), loop).result()

def derive_password():
    password = st.session_state.password_input
    if not password:
        st.warning("Please enter a password to generate.")
        return
    if not token.is_connected:
        connect_to_token()
        authenticate_with_token()
        time.sleep(1)  # Give it a moment to authenticate

    with st.spinner("Generating password..."):
        pw = asyncio.run_coroutine_threadsafe(
            token.generate_password(password), loop
        ).result()
    if pw:
        st.success(f"Generated password: {base64.b64encode(pw).decode('utf-8')}")
    else:
        st.error("Failed to generate password.")

@st.fragment(run_every="1s")
def authentication_badge():
    if token.is_authenticated:
        st.badge("Authenticated", color="green")
    else:
        st.badge("Not authenticated", color="red")

@st.fragment(run_every="5s")
def connection_badge():
        if token.is_connected:
            st.badge("Connected to BLE token!", color="green")
        else:
            st.badge("Not connected", color="red")

with st.container(horizontal=True, vertical_alignment="center"):
    st.title("BLE Security Token")
    with st.container(gap="xsmall"):
        connection_badge()
        authentication_badge()

tab1, tab2, tab3 = st.tabs(["Beacon Mode", "Password Mode", "Settings"])

with tab1:
    st.write("Use your BLE token as a presence beacon to trigger actions on connect/disconnect.")
    with st.container(horizontal=True):
        st.button("Start Beacon", on_click=connect_to_token)
        st.button("Stop Beacon and Disconnect", on_click=lambda: asyncio.run_coroutine_threadsafe(token.disconnect(), loop))

with tab2:
    st.write("Generate strong passwords securely using your BLE token. Authenticate with the token and enter a master password to generate a unique password.")
    st.text_input("Enter password to generate:", key="password_input", type="password")
    st.button("Generate Password", on_click=derive_password)

with tab3:
    st.write("Configure your BLE token settings, including device address, commands to run on connect/disconnect, and RSSI threshold for presence detection.")
    st.text_input("Device Address (MAC):", key="device_address", value=(token.settings.get("device_address") or ""))
    st.text_input("On Connect Command:", key="on_connect_command", value=(token.settings.get("on_connect_command") or ""))
    st.text_input("On Disconnect Command:", key="on_disconnect_command", value=(token.settings.get("on_disconnect_command") or ""))
    st.slider("RSSI Threshold for Presence Detection:", min_value=-100, max_value=0, key="rssi_threshold", value=token.settings.get("rssi_threshold", -80))
    st.text_input("Random Public Key (hex):", key="random_public_key", value=(token.settings.get("random_public_key") or ""))
    st.button("Save Settings", on_click=lambda: token._save_settings())

    

