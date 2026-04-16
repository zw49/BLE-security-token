from ble_token import Token
import asyncio
import base64

RANDOM_PUBLIC_KEY = "042b59c1d7df52300710294d12be4b0df8d35891aa972aaea93805f10f01053a6ff9964ee6545613d77f16bedc3c63b2b16bee67e6bddecd194b259eb8f80229ae"

async def main():
    # password = input("Enter password: ")
    token = Token()
    token.get_public_key()
    token.should_run_commands = False
    await token.connect()
    await token.send_nonce()
    for _ in range(50):
        if token.is_authenticated:
            break
        await asyncio.sleep(0.1)
    else:
        print("Authentication timed out.")
        return
    password = input("Enter password: ")
    pw = await token.generate_password(password, bytes.fromhex(RANDOM_PUBLIC_KEY))
    print(f"Generated password: {base64.b64encode(pw).decode('utf-8')}")

if __name__ == "__main__":
    asyncio.run(main())