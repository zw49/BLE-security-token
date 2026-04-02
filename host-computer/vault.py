# How to update the vault safely:

# * Modify in RAM: Update your dictionary or list of passwords in memory.

# * Serialize: Convert that data back into bytes (e.g., json.dumps(data).encode()).

# * Encrypt: Use your cipher to encrypt those bytes.

# * Overwrite: Write the new encrypted blob back to vault.enc.

import json
import os

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from getpass import getpass


SALT_FILE = "vault.salt"


def derive_key(password: str, salt: bytes) -> bytes:
    return scrypt(password.encode(), salt, key_len=16, N=2**20, r=8, p=1)


class Vault:
    def __init__(self, password: str):
        if os.path.exists(SALT_FILE):
            with open(SALT_FILE, "rb") as f:
                self.salt = f.read()
        else:
            self.salt = os.urandom(16)
            with open(SALT_FILE, "wb") as f:
                f.write(self.salt)
        self.key = self.__derive_key(password, self.salt)

    def load(self):
        with open("vault.enc", "rb") as f:
            nonce = f.read(16)
            tag = f.read(16)
            ciphertext = f.read()
        cipher = AES.new(self.key, AES.MODE_EAX, nonce=nonce)
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
        return json.loads(decrypted_data)

    def save(self, data):
        cipher = AES.new(self.key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(json.dumps(data).encode())
        with open("vault.enc", "wb") as f:
            f.write(cipher.nonce)
            f.write(tag)
            f.write(ciphertext)
    
    def __derive_key(self, password: str, salt: bytes) -> bytes:
        return scrypt(password.encode(), salt, key_len=16, N=2**20, r=8, p=1)


def main():

    password = getpass("Vault password: ")
    vault = Vault(password)

    # Load existing data
    try:
        data = vault.load()
        print("Vault loaded:", data)
    except FileNotFoundError:
        print("No vault found, starting fresh.")
        data = {}
    except ValueError:
        print("Wrong password.")
        return

    # Update the vault in memory
    data["example.com"] = "password123"

    # Save the updated vault
    vault.save(data)
    print("Vault saved.")


if __name__ == "__main__":
    main()
