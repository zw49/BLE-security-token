#include <bluefruit.h>

extern BLEUart bleuart;

void setup() {
  Serial.begin(115200);
  unsigned long start = millis();
  while (!Serial && (millis() - start < 3000)) delay(10);
  // setting up low charging current
  pinMode(13, OUTPUT);

  setup_connections();
  setup_crypto();
  startAdv();
}

void loop() {

  digitalWrite(13, HIGH);
  // Handle USB serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "GET_PUBKEY" || command == "GET_PUB") {
      get_public_key();
    } else {
      Serial.print("UNKNOWN_COMMAND: ");
      Serial.println(command);
    }
  }

  // Handle BLE UART data
  if (bleuart.available()) {
    uint8_t buf[256];
    int count = bleuart.read(buf, sizeof(buf));
    Serial.print("BLE received (");
    Serial.print(count);
    Serial.print(" bytes): ");
    print_hex(buf, count);

    send_signed_nonce(buf, count);
  }
}