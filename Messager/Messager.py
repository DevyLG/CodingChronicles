"""
Messager: A command-line tool for symmetric encryption and decryption.

This script uses the Fernet symmetric encryption algorithm from the `cryptography`
library to securely encrypt and decrypt messages. It operates using a private key
file (defaulting to `private.key`).

Features:
-   Generate a new encryption key.
-   Encrypt a message using the key.
-   Decrypt a message using the key.
-   Interactive command-line interface when run without arguments.

How to Use:
1.  Generate a key (only needs to be done once):
    python Messager.py --genkey
    This creates a `private.key` file in the same directory.

2.  Encrypt a message:
    python Messager.py --encode "Your secret message"

3.  Decrypt a message:
    python Messager.py --decode "gAAAAABf...your_encrypted_message_here..."

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

def get_fernet_instance(keyfile):
    """Loads key from keyfile and returns a Fernet instance.
    
    Exits gracefully if keyfile is missing or malformed.
    """
    try:
        with open(keyfile, 'r') as file:
            key = file.read().strip()
        return fernet.Fernet(key)
    except FileNotFoundError:
        print(Fore.RED + f"[Error] Key file '{keyfile}' not found! Use --genkey to generate one.")
        sys.exit(1)
    except ValueError:
        print(Fore.RED + f"[Error] Invalid key format in '{keyfile}'! Key must be 32 URL-safe base64-encoded bytes.")
        sys.exit(1)
    except Exception as e:
        print(Fore.RED + f"[Error] Error loading key from '{keyfile}': {e}")
        sys.exit(1)

def encryption(msg, keyfile="private.key"):
    """Encrypts a message using the key from the specified key file.

    Args:
        msg (str): The message string to be encrypted.
        keyfile (str): The path to the file containing the key.
    """
    f = get_fernet_instance(keyfile)
    en_msg = f.encrypt(msg.encode())
    
    print(f"{'=' * 25}")
    # Print the encrypted message, decoded back to a string for display.
    print(Fore.GREEN + en_msg.decode())
    print(f"{'=' * 25}")

def decryption(encrypted_msg, keyfile="private.key"):
    """Decrypts an encrypted message using the key from the specified key file.

    Args:
        encrypted_msg (str): The encrypted message string to be decrypted.
        keyfile (str): The path to the file containing the key.
    """
    f = get_fernet_instance(keyfile)
    try:
        # Attempt to decrypt the message.
        de_msg = f.decrypt(encrypted_msg.encode()).decode()
        print(f"{'=' * 25}")
        print(Fore.GREEN + de_msg)
    except fernet.InvalidToken:
        # This error occurs if the key is incorrect or the message is corrupted.
        print(Fore.RED + "Invalid Key or Message!")
    except Exception as e:
        print(Fore.RED + f"Decryption failed: {e}")
    
    print(f"{'=' * 25}")

def generate_key(keyfile="private.key"):
    """Generates a new Fernet encryption key and saves it to the specified key file."""
    try:
        # Generate a new URL-safe base64-encoded key.
        key = fernet.Fernet.generate_key().decode()
        
        # Write the new key to the file, overwriting any existing key.
        with open(keyfile, 'w') as file:
            file.write(key)
            
        # Clear the console for better readability.
        system('cls' if name == 'nt' else 'clear')
        print(Fore.GREEN + f"[Success] Key successfully generated and saved to: {keyfile}")
    except Exception as e:
        print(Fore.RED + f"[Error] Failed to generate key: {e}")

def interactive_mode():
    """Runs a friendly interactive menu for encryption/decryption operations."""
    print(Fore.CYAN + "=========================================")
    print(Fore.CYAN + "        Messager Interactive CLI        ")
    print(Fore.CYAN + "=========================================")
    print("1. Encrypt a message")
    print("2. Decrypt a message")
    print("3. Generate a new encryption key")
    print("4. Exit")
    print(Fore.CYAN + "-----------------------------------------")
    
    while True:
        choice = input(Fore.YELLOW + "Select an option (1-4): ").strip()
        if choice in ('1', '2', '3', '4'):
            break
        print(Fore.RED + "Invalid selection. Please enter 1, 2, 3, or 4.")
        
    if choice == '1':
        msg = input("Enter the message to encrypt: ")
        keyfile = input("Enter key file path (default: private.key): ").strip() or "private.key"
        encryption(msg, keyfile)
    elif choice == '2':
        token = input("Enter the encrypted message: ").strip()
        keyfile = input("Enter key file path (default: private.key): ").strip() or "private.key"
        decryption(token, keyfile)
    elif choice == '3':
        keyfile = input("Enter key file path (default: private.key): ").strip() or "private.key"
        generate_key(keyfile)
    elif choice == '4':
        print("Exiting. Goodbye!")
        sys.exit(0)

def main():
    """Parses command-line arguments and executes the appropriate function."""
    # If no arguments are provided, run interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return

    # Set up the argument parser to handle command-line inputs.
    parser = argparse.ArgumentParser(description="Encryption and Decryption Tool")
    
    # Mutually exclusive group for the primary operations
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-e', '--encode', '-encode', type=str, help="Encrypt the given message")
    group.add_argument('-d', '--decode', '-decode', type=str, help="Decrypt the given message")
    group.add_argument('-g', '--genkey', '-genkey', action='store_true', help="Generate a new encryption key")
    
    # Optional key file parameter
    parser.add_argument('-k', '--keyfile', '-keyfile', type=str, default="private.key", help="Key file path (default: private.key)")
    
    args = parser.parse_args()
    
    if args.genkey:
        generate_key(args.keyfile)
    elif args.encode:
        encryption(args.encode, args.keyfile)
    elif args.decode:
        decryption(args.decode, args.keyfile)

if __name__ == '__main__':
    # This ensures the main function is called only when the script is executed directly.
    main()