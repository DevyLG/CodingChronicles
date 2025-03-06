# Encryption and Decryption Tool

This is a Python-based tool for encrypting and decrypting messages using the **Fernet symmetric encryption** method. It allows the user to encrypt and decrypt messages with a private key and also includes a feature to generate a new key.

## Features
- Encrypt messages with a provided key.
- Decrypt encrypted messages with the same key.
- Generate a new encryption key for securing messages.
- Provides user-friendly output using colors (via `colorama`).




## How to use

- Messager.exe -genkey
- Send the key to your friends. When they gen their own key. You can simple change it to that key
- Messager.exe -encode "Message"
- Messager.exe -decode "Encoded Message"




## If you want to use the python file
Follow the steps below

## Requirements
- Python 3.x
- `cryptography` library
- `colorama` library
- `argparse` (for command-line argument parsing)

### Installing Dependencies

To install the required dependencies, run:

```bash
pip install cryptography colorama