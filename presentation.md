# BLE Security Token Milestone 5

### A Proximity-Based Cryptographic Vault

<small>Cybersecurity Capstone Project · 2026</small>

---

## What is it?

A physical hardware token that:

- Authenticates the user over **BLE**
- Derives **deterministic passwords** bound to the device
- Triggers host actions based on **proximity** (RSSI)
- Uses **ECC P-256** + **ECDH** + **PBKDF2** end to end

Note:
High-level pitch — a single small device replaces password managers, locks your session when you walk away, and cannot be cloned.

---

# 1. The Hardware

---

## Seeed Studio XIAO nRF52840

- **MCU**: Nordic nRF52840 (ARM Cortex-M4F, 64 MHz)
- **Radio**: Bluetooth Low Energy 5.0
- **Storage**: Internal Flash via **LittleFS**
- **Power**: 3.7V LiPo battery, USB-C charging
- **Form factor**: ~21 × 17.5 mm thumbnail-sized board

![image-20260419203308618](/home/z/.config/Typora/typora-user-images/image-20260419203308618.png)

---

## Serial Recovery Channel

On USB, the host can pull the public key at setup:

```cpp
if (command == "GET_PUBKEY" || command == "GET_PUB") {
  get_public_key();  // prints "PUBLIC_KEY: <hex>"
}
```

---

## Different Project Philosophy

- More versatile
- More secure
- More convenient 

# 2. The UI

---

## A Streamlit App

Four pages, one shared `Token` object — [app.py](host-computer/app.py).

```python
pg = st.navigation([
    st.Page("connect.py",  title="Connection", default=True),
    st.Page("beacon.py",   title="Beacon"),
    st.Page("password.py", title="Password"),
    st.Page("settings.py", title="Settings"),
], position="top")
```

Note:
All async BLE work runs on a background event loop spun up once via `@st.cache_resource`, so Streamlit reruns don't disconnect the device.

---

## Shared State

One event loop, one `Token`, survives reruns:

```python
@st.cache_resource
def get_token_and_loop():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return Token(), loop
```

---

## Page 1 · Connection

Shown first. Reads the MAC from settings and connects without scanning.

- Live **Connected / Not Connected** badge, refreshes every 1s
- Connect / Disconnect buttons
- Warns if no device address is configured

---

## Page 2 · Beacon

Turns the token into a **presence detector**:

- Sends a fresh nonce every *N* seconds
- Tracks **RSSI**, runs shell commands when out of range
- Runs `on_connect` / `on_authenticate` / `on_disconnect` hooks

---

## Beacon Loop

```python
async def _beacon_loop(token, interval):
    while True:
        if not token.client or not token.client.is_connected:
            await token.direct_connect()
        else:
            await token.send_nonce()
        await asyncio.sleep(interval)
```

Live card shows last RSSI, last expected/received secret, last ephemeral pubkey.

---

## Page 3 · Password

The headline feature. User types a **site-specific master word** → copies a unique derived password to clipboard.

```python
generated_password = await token.generate_password(password)
decoded_password = base64.b64encode(result).decode('utf-8')
pyperclip.copy(decoded_password)
```

[password.py](host-computer/password.py)

---

# 3. Password Functionality

---

## The Core Idea

A password is **deterministic** given:

1. Your typed master word
2. The device's **private key** (stored only in flash)
3. An **auxiliary public key** (salt-like, per-vault)

Lose the device → passwords unrecoverable.
Clone attempt → can't, private key never leaves the chip.

Note:
This is the inversion of a traditional password manager. Nothing is stored; everything is regenerated on demand from a secret that physically lives on a device you carry.

---

## Step 1 · Authentication (Challenge)

Host generates a nonce + ephemeral ECC keypair, sends both to the token:

```python
nonce = os.urandom(16)
ephemeral_key = ec.generate_private_key(ec.SECP256R1())
ephemeral_public_key = ephemeral_key.public_key().public_bytes(
    Encoding.X962, PublicFormat.UncompressedPoint
)
await self.client.write_gatt_char(
    uart_rx_uuid, nonce + ephemeral_public_key
)
```

[ble_token.py:223-248](host-computer/ble_token/ble_token.py#L223-L248)

---

## Step 1 · Authentication (Response)

Token does ECDH with its **static private key** against the host's **ephemeral public key**, hashes with the nonce, returns 32 bytes:

```cpp
nRFCrypto_ECC::SVDP_DH(privKey, ephemeralPub,
                        sharedSecret, 32);
hash.update(sharedSecret, 32);
hash.update(nonce, 16);          // SHA-256
hash.end(digest);
bleuart.write(digest, 32);
```

[cryptography.ino:190-272](nrf52/ble_token/cryptography.ino#L190-L272)

---

## Step 1 · Authentication (Verify)

Host does the **same ECDH** using the device's known static public key, compares digests:

```python
shared_secret = ephemeral_key.exchange(ec.ECDH(), device_pub)
expected = sha256(shared_secret + nonce).digest()
return expected == device_response
```

Only the real token knows the matching private key → **replay-proof** and **spoof-proof**.

[ble_token.py:150-174](host-computer/ble_token/ble_token.py#L150-L174)

--

## Why Not Just Sign?

ECDH gives us **two wins** in one round-trip:

1. Authentication (only the holder of `privKey` can compute it)
2. A **shared secret** we can reuse as key material for derivation

Signatures authenticate but don't give you a secret to derive from.

---

## Step 2 · Password Derivation

Once authenticated, the host SHA-256s the master word and sends it to the token with an **auxiliary public key**:

```python
hashed_password = sha256(password.encode()).digest()[:16]
await self.client.write_gatt_char(
    uart_rx_uuid,
    hashed_password + bytes.fromhex(
        self.settings.get("random_public_key", "")
    ),
)
```

[ble_token.py:250-274](host-computer/ble_token/ble_token.py#L250-L274)

Note:
The auxiliary pubkey behaves like a domain separator — swap it to get a fresh password universe without re-pairing the hardware.

---

## Step 2 · Derivation (Host Side)

The token's response is stretched with **PBKDF2-HMAC-SHA256**:

```python
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    salt=b"ble_token_salt",
    length=32,          # 256 bits
    iterations=600_000, # OWASP 2023+
)
return kdf.derive(secret)
```

Result → base64 → clipboard.

---

## End-to-End Flow

```
User types "github"
      ↓
SHA-256 → 16 bytes
      ↓ (BLE UART)
Token: ECDH(priv, aux_pub) → sign
      ↓ (BLE UART, 32B)
Host: PBKDF2(secret, 600k iter) → 32B
      ↓
base64 → clipboard
```

Every step is deterministic; none of it is stored.

---

## Presence-Based Lock

RSSI is monitored each notification — [ble_token.py:125-135](host-computer/ble_token/ble_token.py#L125-L135):

```python
if rssi < self.settings.get("rssi_threshold"):
    self._run_command(
        self.settings.get("rssi_below_threshold_command")
    )
    self.is_out_of_range = True
```

Walk away → host auto-locks. Walk back → re-auth triggers unlock command.

---

