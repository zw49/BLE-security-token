#include <Adafruit_nRFCrypto.h>
#include <ecc/nRFCrypto_ECC.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>

using namespace Adafruit_LittleFS_Namespace;

// Filenames for storing keys
const char* privKeyFile = "priv.key";
const char* pubKeyFile = "pub.key";

void setup_crypto() {
  // 1. Initialize the nRFCrypto hardware engine
  if (!nRFCrypto.begin()) {
    Serial.println("Error: Could not initialize nRFCrypto!");
    return;
  }

  // 2. Initialize ECC engine
  nRFCrypto_ECC ecc;
  if (!ecc.begin()) {
    Serial.println("Error: Could not initialize ECC!");
    return;
  }

  // 3. Initialize Internal Flash File System
  if (!InternalFS.begin()) {
    Serial.println("Error: Could not initialize InternalFS!");
    return;
  }

  Serial.println("nRFCrypto & InternalFS initialized.");

  // 4. Declare key objects
  nRFCrypto_ECC_PrivateKey privKey;
  nRFCrypto_ECC_PublicKey pubKey;

  // 5. Try to load keys from flash
  bool keysLoaded = false;
  if (InternalFS.exists(privKeyFile) && InternalFS.exists(pubKeyFile)) {
    Serial.println("Found existing keys in flash. Loading...");

    uint8_t rawPriv[64];
    uint8_t rawPub[128];

    File file = InternalFS.open(privKeyFile, FILE_O_READ);
    if (file) {
      uint32_t sz = file.size();
      Serial.print("Opened private key file, size: ");
      Serial.println(sz);
      uint32_t privLen = file.read(rawPriv, sizeof(rawPriv));
      file.close();

      file = InternalFS.open(pubKeyFile, FILE_O_READ);
      if (file) {
        sz = file.size();
        Serial.print("Opened public key file, size: ");
        Serial.println(sz);
        uint32_t pubLen = file.read(rawPub, sizeof(rawPub));
        file.close();

        // Initialize objects with P256 domain
        privKey.begin(CRYS_ECPKI_DomainID_secp256r1);
        pubKey.begin(CRYS_ECPKI_DomainID_secp256r1);

        Serial.print("Parsing private key (len=");
        Serial.print(privLen);
        Serial.println(")...");
        bool privOk = privKey.fromRaw(rawPriv, privLen);

        // If 64-byte parse fails, try the last 32 bytes (the actual secret)
        if (!privOk && privLen == 64) {
          Serial.println("64-byte parse failed, trying last 32 bytes...");
          privOk = privKey.fromRaw(rawPriv + 32, 32);
        }

        Serial.print("Parsing public key (len=");
        Serial.print(pubLen);
        Serial.println(")...");
        bool pubOk = pubKey.fromRaw(rawPub, pubLen);

        if (privOk && pubOk) {
          keysLoaded = true;
          Serial.println("Keys successfully loaded from flash.");
        } else {
          Serial.print("Error: Failed to parse raw keys. PrivOK: ");
          Serial.print(privOk);
          Serial.print(" PubOK: ");
          Serial.println(pubOk);
        }
      }
    }
  }

  // 6. Generate new keys if loading failed
  if (!keysLoaded) {
    Serial.println("Generating new ECC P256 key pair...");

    privKey.begin(CRYS_ECPKI_DomainID_secp256r1);
    pubKey.begin(CRYS_ECPKI_DomainID_secp256r1);

    if (!nRFCrypto_ECC::genKeyPair(privKey, pubKey)) {
      Serial.println("Error: Key generation failed!");
      return;
    }

    // Save Private Key to Flash
    uint8_t rawPriv[64];
    uint32_t privLen = privKey.toRaw(rawPriv, sizeof(rawPriv));
    File file = InternalFS.open(privKeyFile, FILE_O_WRITE);
    if (file) {
      file.seek(0);
      file.truncate(0);
      file.write(rawPriv, privLen);
      file.close();
      Serial.print("Saved private key (");
      Serial.print(privLen);
      Serial.println(" bytes)");
    }

    // Save Public Key to Flash
    uint8_t rawPub[128];
    uint32_t pubLen = pubKey.toRaw(rawPub, sizeof(rawPub));
    file = InternalFS.open(pubKeyFile, FILE_O_WRITE);
    if (file) {
      file.seek(0);
      file.truncate(0);
      file.write(rawPub, pubLen);
      file.close();
      Serial.print("Saved public key (");
      Serial.print(pubLen);
      Serial.println(" bytes)");
    }

    Serial.println("New keys saved to flash.");
  }

  // 7. Print current keys for verification
  uint8_t rawPriv[64];
  uint32_t privLen = privKey.toRaw(rawPriv, sizeof(rawPriv));
  Serial.print("Private Key (HEX), Length ");
  Serial.print(privLen);
  Serial.print(": ");
  print_hex(rawPriv, privLen);

  uint8_t rawPub[128];
  uint32_t pubLen = pubKey.toRaw(rawPub, sizeof(rawPub));
  Serial.print("Public Key  (HEX), Length ");
  Serial.print(pubLen);
  Serial.print(": ");
  print_hex(rawPub, pubLen);

  // Clean up
  ecc.end();
}

void get_public_key() {
  // We need to re-init to load the public key from flash
  if (!nRFCrypto.begin()) return;
  nRFCrypto_ECC ecc;
  if (!ecc.begin()) return;
  if (!InternalFS.begin()) return;

  nRFCrypto_ECC_PublicKey pubKey;
  if (InternalFS.exists(pubKeyFile)) {
    uint8_t rawPub[128];
    File file = InternalFS.open(pubKeyFile, FILE_O_READ);
    if (file) {
      uint32_t pubLen = file.read(rawPub, sizeof(rawPub));
      file.close();

      pubKey.begin(CRYS_ECPKI_DomainID_secp256r1);
      if (pubKey.fromRaw(rawPub, pubLen)) {
        // Output only the public key
        Serial.print("PUBLIC_KEY: ");
        print_hex(rawPub, pubLen);
      } else {
        Serial.println("ERROR: Failed to parse public key.");
      }
    } else {
      Serial.println("ERROR: Could not open public key file.");
    }
  } else {
    Serial.println("ERROR: Public key file not found.");
  }
  ecc.end();
}

// Receive [16-byte nonce][65-byte ephemeral pubkey], do ECDH, hash, send back over BLE
void send_signed_nonce(uint8_t* input, uint32_t inputLen) {
  if (inputLen != 81) {
    Serial.print("Error: Expected 81 bytes, got ");
    Serial.println(inputLen);
    return;
  }

  uint8_t* nonce = input;
  uint8_t* ephemeralPubRaw = input + 16;

  Serial.print("NONCE: ");
  for (int i = 0; i < 16; i++) {
    Serial.print(nonce[i], HEX);
  }
  Serial.println();

  // Init crypto
  if (!nRFCrypto.begin()) return;
  nRFCrypto_ECC ecc;
  if (!ecc.begin()) return;
  if (!InternalFS.begin()) return;

  // Load private key from flash
  nRFCrypto_ECC_PrivateKey privKey;
  privKey.begin(CRYS_ECPKI_DomainID_secp256r1);

  uint8_t rawPriv[64];
  File file = InternalFS.open(privKeyFile, FILE_O_READ);
  if (!file) {
    Serial.println("Error: Could not open private key file.");
    ecc.end();
    return;
  }
  uint32_t privLen = file.read(rawPriv, sizeof(rawPriv));
  file.close();

  if (!privKey.fromRaw(rawPriv, privLen)) {
    if (privLen == 64) {
      if (!privKey.fromRaw(rawPriv + 32, 32)) {
        Serial.println("Error: Failed to parse private key.");
        ecc.end();
        return;
      }
    } else {
      Serial.println("Error: Failed to parse private key.");
      ecc.end();
      return;
    }
  }

  // Parse host's ephemeral public key
  nRFCrypto_ECC_PublicKey ephemeralPub;
  ephemeralPub.begin(CRYS_ECPKI_DomainID_secp256r1);
  if (!ephemeralPub.fromRaw(ephemeralPubRaw, 65)) {
    Serial.println("Error: Failed to parse ephemeral public key.");
    ecc.end();
    return;
  }

  // ECDH to derive shared secret
  uint8_t sharedSecret[32];
  uint32_t secretLen = nRFCrypto_ECC::SVDP_DH(privKey, ephemeralPub, sharedSecret, sizeof(sharedSecret));
  ecc.end();

  if (secretLen == 0) {
    Serial.println("Error: ECDH failed.");
    return;
  }

  // SHA-256(shared_secret + nonce)
  nRFCrypto_Hash hash;
  hash.begin(CRYS_HASH_SHA256_mode);
  hash.update(sharedSecret, secretLen);
  hash.update(nonce, 16);
  uint8_t digest[32];
  hash.end(digest);

  Serial.print("Signed nonce: ");
  print_hex(digest, 32);

  // Send hash back over BLE
  bleuart.write(digest, 32);
}

// Helper function to print hex values cleanly
void print_hex(uint8_t* buf, uint32_t len) {
  for (uint32_t i = 0; i < len; i++) {
    if (buf[i] < 0x10) Serial.print("0");
    Serial.print(buf[i], HEX);
  }
  Serial.println();
}