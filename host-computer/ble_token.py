import json
import os
import subprocess
import asyncio
from bleak import BleakClient, BleakScanner
import serial
from serial.tools import list_ports
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC



SETTINGS_FILE = "./settings.json"

class Token:
    def __init__(self, settings_path=SETTINGS_FILE):
        self.settings_path = settings_path
        self.settings = self._load_settings()
        self.client = None
        self.is_authenticated = False
        self.should_run_commands = True
        self.is_connected = False
        self._rx_buffer = bytearray()
        self._pending_nonce = None
        self._pending_ephemeral_key = None
        self._generating_password = False

    def _load_settings(self):
        if not os.path.exists(self.settings_path):
            return {
                "public_key": None,
                "on_connect_command": None,
                "on_disconnect_command": None,
                "rssi_threshold": -80
            }
        with open(self.settings_path, "r") as f:
            return json.load(f)

    async def connect(self, address=None):
        """Scan for and connect to the BLE token, then start UART notifications."""
        address = address or self.settings.get("device_address")
        if not address:
            print("No device address provided or configured.")
            return False

        print(f"Scanning for device {address}...")
        device = await BleakScanner.find_device_by_address(address, timeout=10.0)

        if not device:
            print(f"Could not find device with address {address}. Nearby devices:")
            devices = await BleakScanner.discover()
            for d in devices:
                print(f"  {d.address}: {d.name or 'Unknown'}")
            return False

        print(f"Connecting to {address}...")
        self.client = BleakClient(device)
        try:
            await self.client.connect()
            if self.client.is_connected:
                print(f"Connected to {address}!")
                self.is_connected = True

                uart_uuid = self.settings.get("uart_tx_char_uuid")
                if uart_uuid:
                    await self.client.start_notify(uart_uuid, self._notification_handler)
                    print("UART notifications started.")
                if self.should_run_commands:
                    self._run_command(self.settings.get("on_connect_command"))
                return True
        except Exception as e:
            print(f"Connection failed: {e}")

        return False

    def _notification_handler(self, sender, data):
        """Callback for receiving data from the BLE token."""
        self._rx_buffer.extend(data)
        response = bytes(self._rx_buffer)
        print(f"Received data: {response.hex()}", flush=True)


        if len(self._rx_buffer) >= 32 and self._generating_password == False:
            response = bytes(self._rx_buffer[:32])
            self._rx_buffer = self._rx_buffer[32:]
            if self._verify(response):
                print("Authentication successful.", flush=True)
                self.is_authenticated = True
            else:
                print("Authentication failed.", flush=True)
                self.is_authenticated = False

    def _verify(self, device_response):
        """Verify the device's signed nonce response."""
        if not self._pending_nonce or not self._pending_ephemeral_key:
            print("No pending challenge to verify.")
            return False

        device_pub_hex = self.settings.get("public_key")
        device_pub = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), bytes.fromhex(device_pub_hex)
        )

        shared_secret = self._pending_ephemeral_key.exchange(ec.ECDH(), device_pub)
        print(f"Shared secret: {shared_secret.hex()}".upper(), flush=True)
        expected = sha256(shared_secret + self._pending_nonce).digest()

        self._pending_nonce = None
        self._pending_ephemeral_key = None

        print(f"Expected response: {expected.hex()}", flush=True)
        print(f"Device response: {device_response.hex()}", flush=True)

        return expected == device_response

    async def disconnect(self):
        """Disconnect from the BLE token and run disconnect command."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

            if self.should_run_commands:
                self._run_command(self.settings.get("on_disconnect_command"))
            self.client = None

    def _run_command(self, command):
        if command:
            try:
                subprocess.Popen(command, shell=True)
            except Exception as e:
                print(f"Failed to run command '{command}': {e}")

    def get_public_key(self):
        """Return the stored public key."""
        if not self.settings.get("public_key"):
            print("No public key configured. Please plug the device in and press enter to retrieve it.")
            input("Press Enter after plugging in the device...")
            for p in list_ports.comports():
                # print(f"Checking port {p}...")
                if "XIAO nRF52840" in p.description:
                    print(f"Found {p.description}")
                    try:
                        with serial.Serial(p.device, 115200, timeout=1) as ser:
                            ser.write(b"GET_PUB\n")
                            response = ser.readline().decode().strip()
                            if response.startswith("PUBLIC_KEY:"):
                                public_key = str(response.split(":", 1)[1].strip())
                                self.settings["public_key"] = public_key
                                with open(self.settings_path, "w") as f:
                                    json.dump(self.settings, f, indent=4)
                                print(f"Public key retrieved and saved: {public_key}")
                                return public_key
                    except Exception as e:
                        print(f"Error checking port {p.device}: {e}")
        return self.settings.get("public_key")

    async def send_nonce(self):
        """Generate a random nonce and send it to the device over BLE."""
        if not self.client or not self.client.is_connected:
            print("Not connected to device.")
            return None

        nonce = os.urandom(16)
        ephemeral_key = ec.generate_private_key(ec.SECP256R1())
        ephemeral_public_key = ephemeral_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        self._pending_nonce = nonce
        self._pending_ephemeral_key = ephemeral_key

        uart_rx_uuid = self.settings.get("uart_rx_char_uuid")
        self._rx_buffer.clear()
        await self.client.write_gatt_char(uart_rx_uuid, nonce + ephemeral_public_key)
        print(f"Nonce sent: {nonce.hex()}", flush=True)
        print(f"Ephemeral public key sent: {ephemeral_public_key.hex()}", flush=True)
        return nonce
    
    async def generate_password(self, password):
        if not self.client or not self.client.is_connected:
            print("Not connected to device.")
            self.is_connected = False
            return None
        
        if not self.is_authenticated:
            print("Device not authenticated. Cannot generate password.")
            return None
    
        hashed_password = sha256(password.encode()).digest()[:16]
        uart_rx_uuid = self.settings.get("uart_rx_char_uuid")
        self._generating_password = True
        await self.client.write_gatt_char(uart_rx_uuid, hashed_password + bytes.fromhex(self.settings.get("random_public_key", "")))
        await asyncio.sleep(5)  # Wait for response
        self._generating_password = False
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            salt=b"ble_token_salt",
            length=32,            # Output key length (32 bytes = 256 bits)
            iterations=600000,    # High iteration count to slow down attackers
        )
        secret = bytes(self._rx_buffer)
        return kdf.derive(secret)


    async def monitor_rssi(self):
        """Placeholder for RSSI monitoring logic."""
        if self.client and self.client.is_connected:
            # Note: Bleak's get_rssi() behavior varies by platform
            pass


async def main():
    token = Token()
    token.get_public_key()
    await token.connect()

    while True:
        if await token.send_nonce() == None:
            print("Failed to send nonce. Device may be disconnected.")
            await token.connect()
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
