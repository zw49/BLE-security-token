import json
import streamlit as st


def save_settings(updates):
    token = st.session_state.token
    token.settings.update(updates)
    with open(token.settings_path, "w") as f:
        json.dump(token.settings, f, indent=4)


st.title("Settings")
st.write("Configure the BLE token and host behavior. Changes are saved to `settings.json`.")

token = st.session_state.token
s = token.settings

with st.form("settings_form"):
    st.subheader("Device")
    device_address = st.text_input(
        "Device Address (MAC)",
        value=s.get("device_address", ""),
        help="BLE MAC address of the token, e.g. F6:FD:DA:1D:13:E5",
    )
    public_key = st.text_area(
        "Public Key (hex)",
        value=s.get("public_key", ""),
        help="Token's static public key, retrieved via USB on first setup.",
        height=100,
    )
    random_public_key = st.text_area(
        "Random Public Key (hex)",
        value=s.get("random_public_key", ""),
        help="Auxiliary public key used for password derivation.",
        height=100,
    )

    st.subheader("UART Characteristics")
    uart_tx_char_uuid = st.text_input(
        "UART TX Characteristic UUID",
        value=s.get("uart_tx_char_uuid", ""),
        help="Characteristic the host receives notifications on.",
    )
    uart_rx_char_uuid = st.text_input(
        "UART RX Characteristic UUID",
        value=s.get("uart_rx_char_uuid", ""),
        help="Characteristic the host writes to.",
    )

    st.subheader("Beacon")
    beacon_interval_seconds = st.number_input(
        "Beacon Interval (seconds)",
        min_value=1,
        max_value=60,
        value=int(s.get("beacon_interval_seconds", 5)),
    )
    rssi_threshold = st.slider(
        "RSSI Threshold (dBm)",
        min_value=-100,
        max_value=0,
        value=int(s.get("rssi_threshold", -80)),
        help="Host considers the device out of range when RSSI drops below this.",
    )

    st.subheader("Commands")
    on_connect_command = st.text_input(
        "On Connect Command",
        value=s.get("on_connect_command", ""),
        help="Shell command run when the token connects.",
    )
    on_authenticate_command = st.text_input(
        "On Authenticate Command",
        value=s.get("on_authenticate_command", ""),
        help="Shell command run after successful authentication.",
    )
    on_disconnect_command = st.text_input(
        "On Disconnect Command",
        value=s.get("on_disconnect_command", ""),
        help="Shell command run when the token disconnects.",
    )
    rssi_below_threshold_command = st.text_input(
        "RSSI Below Threshold Command",
        value=s.get("rssi_below_threshold_command", ""),
        help="Shell command run when signal drops below the RSSI threshold.",
    )

    submitted = st.form_submit_button("Save Settings", type="primary")

if submitted:
    save_settings({
        "device_address": device_address.strip(),
        "public_key": public_key.strip(),
        "random_public_key": random_public_key.strip(),
        "uart_tx_char_uuid": uart_tx_char_uuid.strip(),
        "uart_rx_char_uuid": uart_rx_char_uuid.strip(),
        "beacon_interval_seconds": int(beacon_interval_seconds),
        "rssi_threshold": int(rssi_threshold),
        "on_connect_command": on_connect_command,
        "on_authenticate_command": on_authenticate_command,
        "on_disconnect_command": on_disconnect_command,
        "rssi_below_threshold_command": rssi_below_threshold_command,
    })
    st.success("Settings saved.")
