import asyncio
import time
import streamlit as st

async def _beacon_loop(token, interval):
    while True:
        if not token.client or not token.client.is_connected:
            await token.direct_connect()
        else:
            await token.send_nonce()
        await asyncio.sleep(interval)


def handle_start_beacon():
    token = st.session_state.token
    loop = st.session_state.loop
    interval = st.session_state.beacon_interval_seconds
    token.should_run_commands = True

    if token.beacon_task is None or token.beacon_task.done():
        token.beacon_task = asyncio.run_coroutine_threadsafe(
            _beacon_loop(token, interval), loop
        )


def handle_stop_beacon():
    token = st.session_state.token
    if token.beacon_task is not None:
        token.beacon_task.cancel()
        token.beacon_task = None


@st.fragment(run_every="1s")
def connection_status():
    with st.container(width="content"):
        token = st.session_state.token
        if token.is_connected:
            st.badge("Connected", color="green")
        else:
            st.badge("Not connected", color="red")

@st.fragment(run_every="1s")
def start_beacon_button():
    task = st.session_state.token.beacon_task
    if task is not None:
        st.button(
            "Stop Beacon",
            key="beacon_toggle",
            width="stretch",
            on_click=handle_stop_beacon,
            disabled=not st.session_state.token.is_connected,
            help="Stop sending presence signals to the token.",
            type="secondary",
        )
    else:
        st.button(
            "Start Beacon",
            key="beacon_toggle",
            width="stretch",
            on_click=handle_start_beacon,
            disabled=not st.session_state.token.is_connected,
            help="Start sending presence signals to the token. Make sure the token is connected.",
            type="primary",
        )

@st.fragment(run_every="1s")
def ping_card():
    with st.container(border=True):
        if not st.session_state.token.beacon_task:
            st.text("Waiting for beacon to start...")
        else:
            token = st.session_state.token
            last_rssi = token.last_rssi
            st.badge("Authenticated" if token.is_authenticated else "Not Authenticated", color="green" if token.is_authenticated else "red", width="stretch")
            with st.container(border=True):
                st.markdown(f"Last Secret Expected: `{st.session_state.token.last_secret_expected}`" if st.session_state.token.last_secret_expected else "No secret expected yet.")
                st.markdown(f"Last Secret Received: `{st.session_state.token.last_secret_received}`" if st.session_state.token.last_secret_received else "No secret received yet.")

            st.subheader(f"Time Since Last Ping: `{int(time.monotonic() - st.session_state.token.last_ping_time)}s`" if st.session_state.token.last_ping_time else "No pings sent yet.")
            if last_rssi is not None:
                st.subheader(f"Last RSSI: `{last_rssi} dBm`")
            else:
                st.text("No RSSI data available yet.")
            
            with st.expander("Last Ephemeral Public Key", expanded=False):
                st.code(f"{token.last_ephemeral_public_key.hex() if token.last_ephemeral_public_key else 'None'}", wrap_lines=True)            



with st.container():
    st.title("Secure Beacon")
    st.text("Use your BLE token as a presence detector to trigger actions on connect/disconnect (configure in settings). Uses Ecplic Curve Cryptography to securely authenticate the beacon and prevent spoofing/replay attacks.")
    connection_status()
    st.divider()

with st.container(horizontal=True, vertical_alignment="bottom"):
    start_beacon_button()
    st.number_input(
        "Beacon Interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.token.settings.get("beacon_interval_seconds", 5),
        key="beacon_interval_seconds",
    )
ping_card()

