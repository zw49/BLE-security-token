/*********************************************************************
 This is an example for our nRF52 based Bluefruit LE modules

 Pick one up today in the adafruit shop!

 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!

 MIT license, check LICENSE for more information
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/
#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <uECC.h>

// BLE Service
BLEDfu bledfu;    // OTA DFU service
BLEDis bledis;    // device information
BLEUart bleuart;  // uart over ble
BLEBas blebas;    // battery

// uint_16_t connection_handle = BLE_CONN_HANDLE_INVALID
unsigned long last_heartbeat_millis = 0;
const long heartbeat_interval = 1000;
int count = 0;

// Use the P-256 curve (Standard for most applications)

//########################## CRYPTO
const struct uECC_Curve_t* curve = uECC_secp256r1();

static int RNG(uint8_t* dest, unsigned size) {
  while (size--) {
    *dest = (uint8_t)analogRead(0) ^ (uint8_t)micros();
    dest++;
  }
  return 1;
}


void createEccKeyPair() {
  // init with our random number generator
  uECC_set_rng(&RNG);

  uint8_t private_key[32];
  uint8_t public_key[64];

  Serial.println("Generating the ECC Key Pair...");

  if (!uECC_make_key(public_key, private_key, curve)) {
    Serial.println("Key generation failed!");
  } else {
    Serial.println("Success!");

    Serial.print("Private Key (Hex): ");
    for (int i = 0; i < 32; i++) {
      if (private_key[i] < 16) Serial.print("0");
      Serial.print(private_key[i], HEX);
    }
    Serial.println();

    Serial.print("Public Key (Hex): ");
    for (int i = 0; i < 64; i++) {
      if (public_key[i] < 16) Serial.print("0");
      Serial.print(public_key[i], HEX);
    }
    Serial.println();
  }
}

//########################################### SETUP

void setup() {
  Serial.begin(115200);

  // Wait for the serial monitor to open (common for native USB boards like nRF52840)
  while (!Serial) delay(10);

  Serial.println("BLE Security Token Heartbeat");
  Serial.println("----------------------------");

  // Call the function to generate and print keys
  createEccKeyPair();

  // Setup the BLE LED to be enabled on CONNECT
  // Note: This is actually the default behavior, but provided
  // here in case you want to control this LED manually via PIN 19
  Bluefruit.autoConnLed(true);

  // Config the peripheral connection with maximum bandwidth
  // more SRAM required by SoftDevice
  // Note: All config***() function must be called before begin()
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);  // Check bluefruit.h for supported values
  //Bluefruit.setName(getMcuUniqueID()); // useful testing with multiple central connections
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);

  // To be consistent OTA DFU should be added first if it exists
  bledfu.begin();

  // Configure and Start Device Information Service
  bledis.setManufacturer("Seeed Studio");
  bledis.setModel("XIAO nRF52840 Plus");
  bledis.begin();

  // Configure and Start BLE Uart Service
  bleuart.begin();

  // Start BLE Battery Service
  blebas.begin();
  blebas.write(100);

  // Set up and start advertising
  startAdv();
}

void startAdv(void) {
  // Advertising packet
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();

  // Include bleuart 128-bit uuid
  Bluefruit.Advertising.addService(bleuart);

  // Secondary Scan Response packet (optional)
  // Since there is no room for 'Name' in Advertising packet
  Bluefruit.ScanResponse.addName();

  /* Start Advertising
   * - Enable auto advertising if disconnected
   * - Interval:  fast mode = 20 ms, slow mode = 152.5 ms
   * - Timeout for fast mode is 30 seconds
   * - Start(timeout) with timeout = 0 will advertise forever (until connected)
   * 
   * For recommended advertising interval
   * https://developer.apple.com/library/content/qa/qa1931/_index.html   
   */
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);  // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);    // number of seconds in fast mode
  Bluefruit.Advertising.start(0);              // 0 = Don't stop advertising after n seconds
}

void loop() {
  unsigned long current_time = millis();
  if (current_time - last_heartbeat_millis >= heartbeat_interval) {
    send_heartbeat(count);
    count += 1;
    last_heartbeat_millis = current_time;
  }
  // Forward data from HW Serial to BLEUART
  while (Serial.available()) {
    // Delay to wait for enough input, since we have a limited transmission buffer
    delay(2);

    uint8_t buf[64];
    int count = Serial.readBytes(buf, sizeof(buf));
    bleuart.write(buf, count);
  }

  // Forward from BLEUART to HW Serial
  while (bleuart.available()) {
    uint8_t ch;
    ch = (uint8_t)bleuart.read();
    Serial.write(ch);
  }
}

// callback invoked when central connects
void connect_callback(uint16_t conn_handle) {
  // Get the reference to current connection
  BLEConnection* connection = Bluefruit.Connection(conn_handle);

  char central_name[32] = { 0 };
  connection->getPeerName(central_name, sizeof(central_name));

  Serial.print("Connected to ");
  Serial.println(central_name);
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle connection where this event happens
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason) {
  (void)conn_handle;
  (void)reason;

  Serial.println();
  Serial.print("Disconnected, reason = 0x");
  Serial.println(reason, HEX);
}

void send_heartbeat(int count) {
  char buffer[32];  // Create the "bucket" for your string

  // Fill the bucket: "Device heartbeat 101"
  int len = snprintf(buffer, sizeof(buffer), "Heartbeat: %d", count);

  // Send only the actual number of characters written
  bleuart.write(buffer, len);
}
