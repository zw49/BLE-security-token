# BLE Security Token: Project Update
---
## Project Overview
- **Goal**: Create a physical hardware token for secure authentication and vault decryption.
- **Hardware**: Seeed Studio XIAO nRF52840.
- **Protocol**: Bluetooth Low Energy (BLE) using UART for command exchange.
- **Security**: Asymmetric Cryptography (ECC P-256) + AES-EAX for storage.
---
## Current Progress: Hardware & Firmware
- **BLE Connectivity**:
  - Device advertises as `SecurityToken_XIAO`.
  - BLE UART service fully functional for bi-directional communication.
- **Cryptography (ECC)**:
  - Using `Adafruit_nRFCrypto` for hardware-accelerated ECC.
  - Automatic key generation (secp256r1) on first boot.
  - **Persistence**: Keys are saved to and loaded from Internal Flash (LittleFS).
- **Heartbeat**:
  - Implementation of a 1Hz heartbeat over BLE UART to signal presence.
---
## Current Progress: Host Software
- **Secure Vault (`vault.py`)**:
  - AES-256-EAX authenticated encryption.
  - `scrypt` Key Derivation Function (KDF) for robust password protection.
  - JSON-based storage for flexible data management.
- **Token Monitor (`heartbeat.py`)**:
  - Python-based BLE client using `bleak`.
  - Automatic discovery and connection to the hardware token.
  - Real-time monitoring of the device's heartbeat signal.
---
## Technical Implementation Details
- **Firmware Stack**: Arduino + Bluefruit nRF52 Library.
- **Storage**: `InternalFileSystem` used for `priv.key` and `pub.key`.
- **Host Stack**: Python 3.12, `pycryptodome`, `bleak`.
---
## Next Steps
1. **Cryptographic Handshake**: Implement a challenge-response protocol where the token signs a host-provided nonce.
2. **Vault Integration**: Link the hardware signature to the vault's decryption key.
3. **Physical Interaction**: Utilize the XIAO's user button for "Press to Authenticate" physical presence confirmation.
4. **CLI Tooling**: Create a unified CLI for managing the vault and token pairing.
