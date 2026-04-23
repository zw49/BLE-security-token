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
import time



SETTINGS_FILE = "./settings.json"

class Token:
    def __init__(self, settings_path=SETTINGS_FILE):
        self.settings_path = settings_path
        self.settings = self._load_settings()
        self.client = None
        self.is_authenticated = False
        self.should_run_commands = True
        self.is_connected = False
        self.is_out_of_range = False
        self.last_rssi = None
        self.beacon_task = None
        self.last_ping_time = None
        self.last_secret_expected = None
        self.last_secret_received = None
        self._rx_buffer = bytearray()
        self._pending_nonce = None
        self._pending_ephemeral_key = None
        self._generating_password = False
        self.last_ephemeral_public_key = None

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
    
    async def direct_connect(self):
        """Directly connect to the BLE token using the configured address."""
        if self.client and self.client.is_connected:
            print("Already connected to device.")
            return True
        address = self.settings.get("device_address")
        if not address:
            print("No device address provided or configured.")
            return False

        print(f"Connecting directly (no scan) to device {address}...")
        self.client = BleakClient(address, disconnected_callback=self._on_disconnect)
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

    async def scan_connect(self, address=None):
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
        self.client = BleakClient(device, disconnected_callback=self._on_disconnect)
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
            self.is_connected = False

        return False

    def _notification_handler(self, sender, data):
        """Callback for receiving data from the BLE token."""
        self._rx_buffer.extend(data)
        response = bytes(self._rx_buffer)
        # print(f"Received data: {response.hex()}", flush=True)
        int.from_bytes(response, byteorder='big', signed=True)

        if len(response) == 1: # RSSI update
            rssi = int.from_bytes(response, byteorder='big', signed=True)
            self.last_rssi = rssi
            # print(f"Received RSSI update: {rssi} dBm", flush=True)
            if rssi < self.settings.get("rssi_threshold"):
                print("RSSI below threshold. Device may be out of range.", flush=True)
                if self.should_run_commands and not self.is_out_of_range:
                    self._run_command(self.settings.get("rssi_below_threshold_command"))
                self.is_out_of_range = True
            else:
                self.is_out_of_range = False

        if len(self._rx_buffer) >= 32 and self._generating_password == False:
            response = bytes(self._rx_buffer[:32])
            self._rx_buffer = self._rx_buffer[32:]
            if self._verify(response):
                print("Authentication successful.", flush=True)
                if self.is_authenticated == False and self.should_run_commands:
                    self._run_command(self.settings.get("on_authenticate_command"))
                self.is_authenticated = True
            else:
                print("Authentication failed.", flush=True)
                self.is_authenticated = False
                self.disconnect()

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
    
        self.last_secret_expected = expected.hex()
        self.last_secret_received = device_response.hex()

        print(f"Expected response: {expected.hex()}", flush=True)
        print(f"Device response: {device_response.hex()}", flush=True)

        return expected == device_response

    async def disconnect(self):
        """Disconnect from the BLE token and run disconnect command."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            self.client = None
            self.is_connected = False

            if self.should_run_commands:
                self._run_command(self.settings.get("on_disconnect_command"))
            self.client = None

    def _run_command(self, command):
        if command:
            try:
                subprocess.Popen(command, shell=True)
            except Exception as e:
                print(f"Failed to run command '{command}': {e}")
    
    def _on_disconnect(self, client):
        self.is_connected = False
        self.is_authenticated = False


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
            self._run_command(self.settings.get("on_disconnect_command"))
            print("Not connected to device.")
            return None

        nonce = os.urandom(16)
        ephemeral_key = ec.generate_private_key(ec.SECP256R1())
        ephemeral_public_key = ephemeral_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        self._pending_nonce = nonce
        self._pending_ephemeral_key = ephemeral_key

        uart_rx_uuid = self.settings.get("uart_rx_char_uuid")
        self._rx_buffer.clear()
        try:
            await self.client.write_gatt_char(uart_rx_uuid, nonce + ephemeral_public_key)
        except Exception as e:
            print(f"Write failed, probably out of range: {e}")
            return None
        print(f"Nonce sent: {nonce.hex()}", flush=True)
        self.last_ping_time = time.monotonic()
        self.last_ephemeral_public_key = ephemeral_public_key
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
        self._rx_buffer.clear()
        await self.client.write_gatt_char(uart_rx_uuid, hashed_password + bytes.fromhex(self.settings.get("random_public_key", "")), response=False)
        await asyncio.sleep(2)  # Wait for response
        self._generating_password = False
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            salt=b"ble_token_salt",
            length=32,            # Output key length (32 bytes = 256 bits)
            iterations=600000,    # High iteration count to slow down attackers
        )
        secret = bytes.fromhex(self.last_secret_received)
        return kdf.derive(secret)


async def main():
    token = Token()
    token.get_public_key()
    await token.direct_connect()

    # token.should_run_commands = False
    # await token.send_nonce()
    # await asyncio.sleep(1)  # Wait for authentication to complete
    # print(await token.generate_password("test"))

    while True:
        if await token.send_nonce() == None:
            print("Failed to send nonce. Device may be disconnected.")
            if token.client:
                while token.client.is_connected == False:
                    print("Attempting to reconnect...")
                    await token.direct_connect()
                    await asyncio.sleep(5)
        if token.is_out_of_range:
            print("Device is out of range. Waiting...")
            await asyncio.sleep(15)
        print(f"LAST RSSI: {token.last_rssi}")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
