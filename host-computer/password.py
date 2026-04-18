import streamlit as st
import asyncio
import base64
import pyperclip


async def _get_password(token, password):
    token.should_run_commands = False
    generated_password = None
    if not password:
        st.warning("Please enter a password to generate.")
        return
    if not token.client or not token.client.is_connected:
        await token.direct_connect()
        await token.send_nonce()
        await asyncio.sleep(1)
    
    generated_password = await token.generate_password(password)
    
    return generated_password

def get_password():
    token = st.session_state.token 
    password = st.session_state.password_input
    with st.spinner("Generating password..."):
        result = asyncio.run_coroutine_threadsafe(_get_password(token, password), st.session_state.loop).result()
        if result:
            decoded_password = base64.b64encode(result).decode('utf-8')
            pyperclip.copy(decoded_password)
            st.success(f"Password copied to clipboard")

def main():
    st.title("Password Generator")
    st.write("Generate strong passwords securely using your BLE token. Authenticate with the token and enter a master password to generate a unique password.")
    st.text_input("Enter password to generate:", key="password_input", type="password")
    st.button("Generate Password", on_click=get_password)

if __name__ == "__main__":
    main()