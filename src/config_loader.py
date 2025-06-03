import yaml
import os

def load_accounts_config(config_path="config/accounts.yml"):
    """Loads the accounts configuration from a YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and "accounts" in config and isinstance(config["accounts"], list):
                return config["accounts"]
            else:
                print(f"Warning: 'accounts' key not found or not a list in {config_path}. Returning empty list.")
                return []
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found. Returning empty list.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {config_path}: {e}. Returning empty list.")
        return []

def load_rules_config(config_path="config/rules.yml"):
    """Loads the rules configuration from a YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and "rules" in config and isinstance(config["rules"], list):
                return config["rules"]
            else:
                print(f"Warning: 'rules' key not found or not a list in {config_path}. Returning empty list.")
                return []
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found. Returning empty list.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {config_path}: {e}. Returning empty list.")
        return []

if __name__ == '__main__':
    # Existing example usage for accounts...
    accounts = load_accounts_config()
    if accounts:
        print("Accounts loaded successfully:")
        for account in accounts:
            print(f"  Name: {account.get('name')}, Type: {account.get('type')}, Identifier: {account.get('identifier')}")
    else:
        print("No accounts were loaded.")

    print("\nTesting with a non-existent accounts file:")
    accounts_non_existent = load_accounts_config("config/non_existent.yml")
    if not accounts_non_existent:
        print("Correctly handled non-existent accounts file.")

    # Test with an invalid YAML file for accounts
    print("\nTesting with an invalid accounts YAML file:")
    # Create a temporary invalid accounts file
    invalid_accounts_path = "config/invalid_accounts.yml"
    with open(invalid_accounts_path, 'w', encoding='utf-8') as f:
        f.write("accounts: [{name: Test, type: bank, identifier: 1234}]") # Slightly better invalid YAML for testing this part
    accounts_invalid = load_accounts_config(invalid_accounts_path)
    if not accounts_invalid:
        print("Correctly handled invalid accounts YAML file.")
    if os.path.exists(invalid_accounts_path):
        os.remove(invalid_accounts_path)


    print("\nTesting with missing 'accounts' key:")
    # Create a temporary missing key accounts file
    missing_key_accounts_path = "config/missing_key_accounts.yml"
    with open(missing_key_accounts_path, 'w', encoding='utf-8') as f:
        f.write("other_key: value")
    accounts_missing_key = load_accounts_config(missing_key_accounts_path)
    if not accounts_missing_key:
        print("Correctly handled missing 'accounts' key.")
    if os.path.exists(missing_key_accounts_path):
        os.remove(missing_key_accounts_path)

    print("\n" + "="*20 + "\n") # Separator

    # Example usage for rules:
    rules = load_rules_config()
    if rules:
        print("Rules loaded successfully:")
        for rule in rules:
            print(f"  Name: {rule.get('name')}, Account: {rule.get('account')}, Keywords: {rule.get('conditions', {}).get('keywords')}")
    else:
        print("No rules were loaded.")

    # Test with a non-existent rules file
    print("\nTesting with a non-existent rules file:")
    rules_non_existent = load_rules_config("config/non_existent_rules.yml")
    if not rules_non_existent:
        print("Correctly handled non-existent rules file.")

    # Test with an invalid YAML file for rules
    print("\nTesting with an invalid rules YAML file:")
    # Create a temporary invalid rules file
    invalid_rules_path = "config/invalid_rules.yml"
    with open(invalid_rules_path, 'w', encoding='utf-8') as f:
        f.write("rules: [{name: Test Rule, account: Test Account}]") # Slightly better invalid YAML
    rules_invalid = load_rules_config(invalid_rules_path)
    if not rules_invalid:
        print("Correctly handled invalid rules YAML file.")
    if os.path.exists(invalid_rules_path):
        os.remove(invalid_rules_path)

    # Test with missing 'rules' key
    print("\nTesting with missing 'rules' key:")
    # Create a temporary missing key rules file
    missing_key_rules_path = "config/missing_key_rules.yml"
    with open(missing_key_rules_path, 'w', encoding='utf-8') as f:
        f.write("other_data: some_value")
    rules_missing_key = load_rules_config(missing_key_rules_path)
    if not rules_missing_key:
        print("Correctly handled missing 'rules' key.")
    if os.path.exists(missing_key_rules_path):
        os.remove(missing_key_rules_path)
