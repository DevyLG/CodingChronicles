import argparse
from os import system, name
from cryptography import fernet
from colorama import Fore, init
import sys  # Add this import to use sys.exit()

init(autoreset=True)

def encryption(msg):
    with open('private.key', 'r') as file:
        key = file.read()
        
    f = fernet.Fernet(key)
    en_msg = f.encrypt(msg.encode())
    
    print(f"{'=' * 25}")
    print(Fore.GREEN + en_msg.decode())
    print(f"{'=' * 25}")

def decryption(encrypted_msg):
    with open('private.key', 'r') as file:
        key = file.read()
        
    f = fernet.Fernet(key)
    try:
        de_msg = f.decrypt(encrypted_msg.encode()).decode()
        print(f"{'=' * 25}")
        print(Fore.GREEN + de_msg)
    except fernet.InvalidToken:
        print(Fore.RED + "Invalid Key or Message!")
    
    print(f"{'=' * 25}")

def generate_key():
    key = fernet.Fernet.generate_key().decode()
    
    with open('private.key', 'w') as file:
        file.write(key)
        
    system('cls' if name == 'nt' else 'clear')
    print(f'New key generated: {Fore.GREEN + key}')

def main():
    parser = argparse.ArgumentParser(description="Encryption and Decryption Tool")
    
    parser.add_argument('-encode', type=str, help="Encrypt the given message")
    parser.add_argument('-decode', type=str, help="Decrypt the given message")
    parser.add_argument('-genkey', action='store_true', help="Generate a new encryption key")
    
    args = parser.parse_args()
    
    if args.genkey:
        generate_key()
    elif args.encode or args.decode:
        try:
            with open('private.key', 'r') as file:
                pass
        except FileNotFoundError:
            print(Fore.RED + "private.key not found! Use -genkey to generate one.")
            sys.exit(1)  # Use sys.exit() instead of exit()
        if args.encode:
            encryption(args.encode)
        elif args.decode:
            decryption(args.decode)
    else:
        print("No valid option provided. Use -h for help.")

if __name__ == '__main__':
    main()
