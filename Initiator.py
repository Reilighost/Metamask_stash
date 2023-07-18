import subprocess
import os
import configparser


config_path = 'config.ini'
if os.path.exists(config_path):
    print("Config file found, you can change it manually if needed.")
else:
    max_simultaneous_profiles = input("Enter max simultaneous profiles you machine can run: ")
    metamask_identificator = input("Enter metamask Identificator: ")

    # Create a new config object
    config = configparser.ConfigParser()

    # Populate the config object with user input
    config['DEFAULT'] = {
        'max_simultaneous_profiles': max_simultaneous_profiles,
        'metamask_identificator': metamask_identificator,
    }

    # Write the config to a file
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print("Configuration saved.")


def main():
    print("Welcome! Please select the script you want to run:")
    print("1. Import you seed-phrases to profiles")
    print("2. Add standard popular chain")
    print("3. Add USDC to 6 major chain")

    choice = input("Enter your choice: ")

    if choice == "1":
        subprocess.run(['python', 'MetaMask_autoimport.py'])
    elif choice == "2":
        subprocess.run(['python', 'Add_popular_chain.py'])
    elif choice == "3":
        subprocess.run(['python', 'Metamask_add_USDC.py'])
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
