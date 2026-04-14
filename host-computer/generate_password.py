import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from ble_token import Token
import asyncio


RANDOM_PUBLIC_KEY = "042b59c1d7df52300710294d12be4b0df8d35891aa972aaea93805f10f01053a6ff9964ee6545613d77f16bedc3c63b2b16bee67e6bddecd194b259eb8f80229ae"

async def main():
    password = input("Enter password: ")
    token = Token()
    token.get_public_key()
    await token.connect()



if __name__ == "__main__":
    asyncio.run(main())