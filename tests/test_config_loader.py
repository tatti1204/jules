import unittest
import os
import yaml
# Ensure load_accounts_config is also imported if you keep tests for it in the same class
from src.config_loader import load_accounts_config, load_rules_config

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        self.test_config_dir = "tests/temp_config"
        os.makedirs(self.test_config_dir, exist_ok=True)

        # Accounts files
        self.valid_accounts_file = os.path.join(self.test_config_dir, "valid_accounts.yml")
        self.invalid_accounts_file = os.path.join(self.test_config_dir, "invalid_accounts.yml") # Used for invalid content
        self.empty_accounts_file = os.path.join(self.test_config_dir, "empty_accounts.yml") # Used for missing 'accounts' key
        self.malformed_accounts_file = os.path.join(self.test_config_dir, "malformed_accounts.yml")


        with open(self.valid_accounts_file, 'w', encoding='utf-8') as f:
            yaml.dump({
                "accounts": [
                    {"name": "Test Bank", "type": "bank", "identifier": "T123"},
                    {"name": "Test CC", "type": "credit_card", "identifier": "T456"}
                ]
            }, f)
        with open(self.empty_accounts_file, 'w', encoding='utf-8') as f:
            yaml.dump({}, f) # Missing 'accounts' key
        with open(self.malformed_accounts_file, 'w', encoding='utf-8') as f:
            yaml.dump({"accounts": {"name": "Test Bank", "type": "bank", "identifier": "T123"}}, f) # 'accounts' is not a list


        # Rules files
        self.valid_rules_file = os.path.join(self.test_config_dir, "valid_rules.yml")
        self.invalid_rules_file = os.path.join(self.test_config_dir, "invalid_rules.yml") # Used for invalid content
        self.empty_rules_file = os.path.join(self.test_config_dir, "empty_rules.yml") # Used for missing 'rules' key
        self.malformed_rules_file = os.path.join(self.test_config_dir, "malformed_rules.yml")


        with open(self.valid_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump({
                "rules": [
                    {"name": "Rule 1", "conditions": {"keywords": ["test"]}, "account": "Test Account"}
                ]
            }, f)
        with open(self.empty_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump({}, f) # Missing 'rules' key
        with open(self.malformed_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump({"rules": {"name": "Rule 1", "account": "Test Account"}}, f) # 'rules' is not a list


    def tearDown(self):
        files_to_remove = [
            self.valid_accounts_file, self.invalid_accounts_file, self.empty_accounts_file, self.malformed_accounts_file,
            self.valid_rules_file, self.invalid_rules_file, self.empty_rules_file, self.malformed_rules_file
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        if os.path.exists(self.test_config_dir):
            # Attempt to remove directory, but handle potential errors if files were not deleted
            try:
                os.rmdir(self.test_config_dir)
            except OSError as e:
                print(f"Error removing directory {self.test_config_dir}: {e}")


    # --- Account Config Tests (from previous step) ---
    def test_load_valid_accounts(self):
        accounts = load_accounts_config(self.valid_accounts_file)
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]["name"], "Test Bank")

    def test_load_non_existent_accounts_file(self):
        accounts = load_accounts_config("tests/non_existent_accounts.yml")
        self.assertEqual(accounts, [])

    def test_load_invalid_yaml_accounts_file(self):
        with open(self.invalid_accounts_file, 'w', encoding='utf-8') as f:
            f.write("accounts: - name: Test:") # Invalid YAML - colon in unquoted string
        accounts = load_accounts_config(self.invalid_accounts_file)
        self.assertEqual(accounts, [])

    def test_load_empty_or_malformed_accounts_key(self):
        accounts_empty = load_accounts_config(self.empty_accounts_file) # 'accounts' key missing
        self.assertEqual(accounts_empty, [])
        accounts_malformed = load_accounts_config(self.malformed_accounts_file) # 'accounts' is not a list
        self.assertEqual(accounts_malformed, [])

    # --- Rules Config Tests ---
    def test_load_valid_rules(self):
        rules = load_rules_config(self.valid_rules_file)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["name"], "Rule 1")

    def test_load_non_existent_rules_file(self):
        rules = load_rules_config("tests/non_existent_rules.yml")
        self.assertEqual(rules, [])

    def test_load_invalid_yaml_rules_file(self):
        with open(self.invalid_rules_file, 'w', encoding='utf-8') as f:
            f.write("rules: - name: Test Rule:") # Invalid YAML - colon in unquoted string
        rules = load_rules_config(self.invalid_rules_file)
        self.assertEqual(rules, [])

    def test_load_empty_or_malformed_rules_key(self):
        rules_empty = load_rules_config(self.empty_rules_file) # 'rules' key missing
        self.assertEqual(rules_empty, [])
        rules_malformed = load_rules_config(self.malformed_rules_file) # 'rules' is not a list
        self.assertEqual(rules_malformed, [])

if __name__ == '__main__':
    unittest.main()
