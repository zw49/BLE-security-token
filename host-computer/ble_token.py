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



SETTINGS_FILE = "./settings.json"

class Token:
    def __init__(self, settings_path=SETTINGS_FILE):
        self.settings_path = settings_path
        self.settings = self._load_settings()
        self.client = None
        self.is_authenticated = False

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

                uart_uuid = self.settings.get("uart_tx_char_uuid")
                if uart_uuid:
                    await self.client.start_notify(uart_uuid, self._notification_handler)
                    print("UART notifications started.")

                self._run_command(self.settings.get("on_connect_command"))
                return True
        except Exception as e:
            print(f"Connection failed: {e}")
        return False

    def _notification_handler(self, sender, data):
        """Callback for receiving data from the BLE token."""
        print(f"Received: {data.hex()}")

    async def disconnect(self):
        """Disconnect from the BLE token and run disconnect command."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
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
        signed_nonce = self.sign_nonce(nonce)
        uart_rx_uuid = self.settings.get("uart_rx_char_uuid")
        await self.client.write_gatt_char(uart_rx_uuid, signed_nonce)
        print(f"Nonce: {nonce.hex()}")
        print(f"Signed nonce sent: {signed_nonce.hex()}")
        return nonce

    async def monitor_rssi(self):
        """Placeholder for RSSI monitoring logic."""
        if self.client and self.client.is_connected:
            # Note: Bleak's get_rssi() behavior varies by platform
            pass
    
    def sign_nonce(self, nonce):
        """Sign the nonce using the stored public key (placeholder)."""
        ephemeral_key = ec.generate_private_key(ec.SECP256R1())
        signature = ephemeral_key.sign(nonce, ec.ECDSA(hashes.SHA256()))
        return signature

async def main():
    token = Token()
    token.get_public_key()
    await token.connect()
    while True:
        await token.send_nonce()
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
