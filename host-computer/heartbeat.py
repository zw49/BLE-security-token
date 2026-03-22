import asyncio
import sys
from bleak import BleakScanner, BleakClient

# Default address or one provided as an argument
DEFAULT_ADDRESS = "F6:FD:DA:1D:13:E5"

# Nordic UART Service TX Characteristic UUID
UART_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

def notification_handler(sender, data):
    """Callback for receiving data from the Arduino."""
    try:
        print(".", end="", flush=True)
    except Exception as e:
        print(f"Received raw data: {data.hex()}")

async def main(address):
    print(f"Scanning for device {address}...")
    device = await BleakScanner.find_device_by_address(address, timeout=10.0)
    
    if not device:
        print(f"Could not find device with address {address}. Here are nearby devices:")
        devices = await BleakScanner.discover()
        for d in devices:
            print(f"  {d.address}: {d.name or 'Unknown'}")
        return

    print(f"Connecting to {address}...")
    try:
        async with BleakClient(device) as client:
            if client.is_connected:
                print(f"Connected to {address}!")
                
                # Model Number String characteristic UUID
                MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
                try:
                    model_number = await client.read_gatt_char(MODEL_NUMBER_UUID)
                    print(f"Model Number: {model_number.decode()}")
                except Exception as e:
                    print(f"Could not read model number: {e}")

                # Start notifications for UART TX
                print("Attempting to receive UART heartbeat...")
                await client.start_notify(UART_TX_CHAR_UUID, notification_handler)
                
                print("Press Ctrl+C to disconnect...")
                while True:
                    await asyncio.sleep(1)
            else:
                print(f"Failed to connect to {address}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    target_address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    try:
        asyncio.run(main(target_address))
    except KeyboardInterrupt:
        print("\nDisconnected.")
