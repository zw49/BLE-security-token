#include <bluefruit.h>
void setup() {
  Serial.begin(115200);
  unsigned long start = millis();
  while (!Serial && (millis() - start < 3000)) delay(10);

  Serial.println("hi");

  setup_connections();
  setup_crypto();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove whitespace/newlines

    if (command == "GET_PUBKEY") {
      // We will need to make the public key accessible or re-extract it
      // For now, let's just trigger setup_crypto again to see it print
      Serial.println("COMMAND_RECEIVED: Sending Public Key...");
      setup_crypto();
    } else {
      Serial.print("UNKNOWN_COMMAND: ");
      Serial.println(command);
    }
  }
}