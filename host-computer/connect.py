import asyncio
import streamlit as st


async def _connect(token):
    if not token.client or not token.client.is_connected:
        await token.disconnect()  # Ensure any existing connection is closed before connecting
        await token.direct_connect()


def handle_connect():
    token = st.session_state.token
    loop = st.session_state.loop
    with st.spinner("Connecting to device..."):
        try:
            asyncio.run_coroutine_threadsafe(_connect(token), loop).result(timeout=15)
        except Exception as e:
            st.error(f"Failed to connect: {e}")


def handle_disconnect():
    token = st.session_state.token
    loop = st.session_state.loop
    with st.spinner("Disconnecting..."):
        try:
            asyncio.run_coroutine_threadsafe(token.disconnect(), loop).result(timeout=10)
        except Exception as e:
            st.error(f"Failed to disconnect: {e}")


@st.fragment(run_every="1s")
def connection_status():
    token = st.session_state.token
    if token.is_connected:
        st.badge("Connected", color="green")
    else:
        st.badge("Not connected", color="red")


st.title("BLE Security Token")
st.write(
    "Connect your BLE security token to get started. "
    "Once connected, you can use it as a presence beacon or to generate secure passwords."
)

st.divider()

with st.container(horizontal=True, vertical_alignment="center"):
    st.subheader("Device Status")
    connection_status()

token = st.session_state.token
address = token.settings.get("device_address")
if address:
    st.caption(f"Configured device: `{address}`")
else:
    st.warning("No device address configured. Go to Settings to add one.")

with st.container(horizontal=True):
    st.button(
        "Connect",
        on_click=handle_connect,
        disabled=token.is_connected or not address,
        type="primary",
    )
    st.button(
        "Disconnect",
        on_click=handle_disconnect,
        disabled=not token.is_connected,
    )
