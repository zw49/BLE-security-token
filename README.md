# Proximity-Based Cryptographic Vault with Physical Anti-Forensic Trigger

This repository contains the source code and hardware specifications for my **Cybersecurity Capstone Project**. The project focuses on bridging the gap between hardware-based authentication and endpoint security through a "Zero Trust" physical proximity model.

---

## 🛡️ Project Overview
The goal of this project is to mitigate the risk of unauthorized physical access to sensitive data when a user steps away from their workstation. It utilizes a **Seeed Studio XIAO nRF52840 (BLE)** microcontroller as a wireless security token. The computer automatically mounts an encrypted data vault when the token is within a specific range and immediately dismounts the vault when the token is removed or the signal is lost.

## 🗝️ Key Features
* **RSA Challenge-Response Authentication:** To prevent device spoofing, the host computer sends a random nonce that the BLE token must sign using a **Private RSA Key** stored locally in its flash memory.
* **Proximity-Based Locking:** The system monitors the Bluetooth signal strength (RSSI) and heartbeat; if the device moves out of range or is disconnected, the vault is locked and dismounted automatically.
* **Physical "Self-Destruct" Button:** A high-priority anti-forensic feature. When the physical button on the BLE token is pressed, it:
    1. Sends a "Kill" signal to the host to **shred** the encrypted vault headers.
    2. **Wipes its own internal memory**, deleting the RSA Private Key to render the vault cryptographically unrecoverable.



## 🛠️ Tech Stack
* **Hardware:** Seeed Studio XIAO nRF52840 Plus, 3.7V LiPo Battery.
* **Firmware:** C++ (Arduino IDE) utilizing the Adafruit Bluefruit nRF52 library.
* **Host Software:** Python-based monitoring service using the `bleak` library for BLE and `cryptography` for RSA verification.
* **Encryption:** Custom AES-256 wrappers or VeraCrypt integration.

## 📅 Project Milestones
* **Milestone 1:** Research on RSA implementation and NIST SP 800-88 sanitization standards [cite: 54-58].
* **Milestone 2:** Environment setup and establishment of a stable BLE "Heartbeat" [cite: 58-62].
* **Milestone 3:** Implementation of the RSA signing protocol [cite: 63-67].
* **Milestone 4:** Integration of the "Self-Destruct" interrupt logic and secure file erasure [cite: 68-72].
* **Milestone 5:** Final testing, range analysis, and technical report submission [cite: 73-77].

---
*Developed as part of a Cybersecurity Capstone Project, 2026.*
