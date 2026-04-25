# BLE Security Token

A proximity-based security system that uses a physical BLE token (nRF52840) to automate host security actions and manage encrypted data.

## 🚀 Overview

This project consists of two main components:
1.  **Firmware:** C++/Arduino code for a Seeed Studio XIAO nRF52840 that handles secure challenge-response authentication using hardware-accelerated ECC.
2.  **Host Software:** A Streamlit-based Python application that monitors the token's proximity via RSSI and performs actions like mounting/unmounting a vault or executing custom commands.

## 🛡️ Key Features

*   **ECC Challenge-Response:** Mutual authentication using secp256r1 (P-256) curves. The host verifies the token's identity before performing sensitive operations.
*   **Proximity-Based Actions:** Automatically run scripts or lock/unlock your computer when the token moves out of range (RSSI threshold).
*   **Encrypted Vault:** A secure storage system using AES-256 (EAX mode) and Scrypt for key derivation, integrated into the host software.
*   **Password Generator:** Generate high-entropy passwords derived from the secure shared secret between the host and token.
*   **Headless/GUI Modes:** Run as a background service or through the interactive Streamlit dashboard.

## 📦 Dependencies

### Host (Python)
Install via `pip`:
```bash
pip install streamlit bleak cryptography pyserial pycryptodome pyperclip
```

### Firmware (Arduino)
Required libraries (available in Arduino Library Manager):
*   `Adafruit Bluefruit nRF52` (by Adafruit)
*   `Adafruit_nRFCrypto` (by Adafruit)
*   `Adafruit_LittleFS` (by Adafruit)

## 📂 Project Structure

*   `nrf52/ble_token/`: Arduino source code for the security token.
*   `host-computer/`: Python source code for the host application.
    *   `app.py`: Main Streamlit entry point.
    *   `ble_token/`: Core BLE and cryptographic logic.
    *   `vault.py`: Encrypted vault management.
    *   `settings.json`: Configuration for MAC addresses, RSSI thresholds, and commands.

## 🛠️ Setup

1.  **Flash the Token:** Open `nrf52/ble_token/ble_token.ino` in Arduino IDE and flash it to your XIAO nRF52840.
2.  **Retrieve Public Key:** Run `python host-computer/ble_token/ble_token.py` while the device is connected via USB to pair and save the token's public key.
3.  **Run Host App:**
    ```bash
    cd host-computer
    streamlit run app.py
    ```
