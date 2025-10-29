"""
Messager: A command-line tool for symmetric encryption and decryption.

This script uses the Fernet symmetric encryption algorithm from the `cryptography`
library to securely encrypt and decrypt messages. It operates using a `private.key`
file for the encryption key.

Features:
-   Generate a new encryption key.
-   Encrypt a message using the key.
-   Decrypt a message using the key.

How to Use:
1.  Generate a key (only needs to be done once):
    python Messager.py -genkey
    This creates a `private.key` file in the same directory.

2.  Encrypt a message:
    python Messager.py -encode "Your secret message"

3.  Decrypt a message:
    python Messager.py -decode "gAAAAABf...your_encrypted_message_here..."

Dependencies:
-   cryptography
-   colorama
-   argparse
"""
import argparse
from os import system, name
from cryptography import fernet
from colorama import Fore, init
import sys

# Initialize colorama to automatically reset style changes after each print.
init(autoreset=True)

def encryption(msg):
    """Encrypts a message using the key from 'private.key'.

    Args:
        msg (str): The message string to be encrypted.
    """
    # Read the encryption key from the file.
    with open('private.key', 'r') as file:
        key = file.read()
        
    # Create a Fernet instance with the key.
    f = fernet.Fernet(key)
    # Encrypt the message. The message must be encoded to bytes first.
    en_msg = f.encrypt(msg.encode())
    
    print(f"{'=' * 25}")
    # Print the encrypted message, decoded back to a string for display.
    print(Fore.GREEN + en_msg.decode())
    print(f"{'=' * 25}")

def decryption(encrypted_msg):
    """Decrypts an encrypted message using the key from 'private.key'.

    Args:
        encrypted_msg (str): The encrypted message string to be decrypted.
    """
    # Read the encryption key from the file.
    with open('private.key', 'r') as file:
        key = file.read()
        
    f = fernet.Fernet(key)
    try:
        # Attempt to decrypt the message.
        de_msg = f.decrypt(encrypted_msg.encode()).decode()
        print(f"{'=' * 25}")
        print(Fore.GREEN + de_msg)
    except fernet.InvalidToken:
        # This error occurs if the key is incorrect or the message is corrupted.
        print(Fore.RED + "Invalid Key or Message!")
    
    print(f"{'=' * 25}")

def generate_key():
    """Generates a new Fernet encryption key and saves it to 'private.key'."""
    # Generate a new URL-safe base64-encoded key.
    key = fernet.Fernet.generate_key().decode()
    
    # Write the new key to the file, overwriting any existing key.
    with open('private.key', 'w') as file:
        file.write(key)
        
    # Clear the console for better readability.
    system('cls' if name == 'nt' else 'clear')
    print(f'New key generated: {Fore.GREEN + key}')

def main():
    """Parses command-line arguments and executes the appropriate function."""
    # Set up the argument parser to handle command-line inputs.
    parser = argparse.ArgumentParser(description="Encryption and Decryption Tool")
    
    parser.add_argument('-encode', type=str, help="Encrypt the given message")
    parser.add_argument('-decode', type=str, help="Decrypt the given message")
    parser.add_argument('-genkey', action='store_true', help="Generate a new encryption key")
    
    args = parser.parse_args()
    
    if args.genkey:
        generate_key()
    elif args.encode or args.decode:
        # Before encrypting or decrypting, ensure a key file exists.
        try:
            with open('private.key', 'r') as file:
                pass
        except FileNotFoundError:
            print(Fore.RED + "private.key not found! Use -genkey to generate one.")
            sys.exit(1)
            
        if args.encode:
            encryption(args.encode)
        elif args.decode:
            decryption(args.decode)
    else:
        # If no arguments are provided, show a help message.
        print("No valid option provided. Use -h for help.")

if __name__ == '__main__':
    # This ensures the main function is called only when the script is executed directly.
    main()