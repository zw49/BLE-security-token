import streamlit as st

def handle_beacon_toggle():
    while st.session_state.beacon_toggle:
        st.info("Beacon is active. Broadcasting BLE signal...")
        # Here you would add the actual BLE broadcasting logic using your token
        # For example, you could call a method like st.session_state.token.start_beacon()
        # and handle stopping it when the toggle is turned off.
        # This is a placeholder for demonstration purposes.
        import time
        time.sleep(5)  # Simulate beacon broadcasting

with st.container(horizontal=True, vertical_alignment="center"):
    st.title("BLE Security Beacon")
    st.toggle("Start Beacon", disabled=False, key="beacon_toggle", on_change=handle_beacon_toggle)