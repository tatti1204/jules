import argparse
import os
import logging
from datetime import datetime, date # Added date
from decimal import Decimal
import csv # Added for the __main__ setup block

# Import project modules
from src.config_loader import load_accounts_config, load_rules_config
from src.statement_parser import parse_statement_csv
from src.voucher_processor import ocr_placeholder, structure_voucher_data
from src.matching_engine import match_transactions_to_vouchers
from src.journal_generator import generate_journal_entries
from src.trial_balance_generator import generate_trial_balance

# Basic Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Default file paths (can be overridden by CLI args) ---
DEFAULT_ACCOUNTS_PATH = "config/accounts.yml"
DEFAULT_RULES_PATH = "config/rules.yml"
# For statements, we'll expect a path to a directory or a specific file.
# For vouchers, we'll use a placeholder mechanism for now.
DEFAULT_OUTPUT_DIR = "output" # All generated files will go here
DEFAULT_TRIAL_BALANCE_FILENAME = "trial_balance.csv"
DEFAULT_JOURNAL_ENTRIES_FILENAME = "journal_entries.json" # Optional: save generated JEs

def ensure_output_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Created output directory: {path}")

def process_vouchers_placeholder(num_vouchers_to_simulate=3):
    """
    Simulates processing a number of vouchers using the ocr_placeholder
    and structure_voucher_data functions. In a real scenario, this would
    iterate over actual voucher files (images/PDFs).
    """
    simulated_vouchers = []
    for i in range(num_vouchers_to_simulate):
        # Give some variation to the placeholder for slightly different vouchers
        placeholder_data = ocr_placeholder(f"simulated_voucher_{i+1}.pdf")
        if i % 2 == 0 and "Example Store" in placeholder_data["vendor_name"]: # Make one different
            placeholder_data["vendor_name"] = "Another Vendor Co"
            placeholder_data["total_amount"] = "75.20"
            placeholder_data["line_items"] = [{"description": "Service X", "quantity": 1, "unit_price": "75.20", "total_price": "75.20"}]

        # Simulate giving a unique ID to each voucher if structure_voucher_data doesn't
        structured = structure_voucher_data(placeholder_data)
        if structured:
            structured['id'] = f"vouchSim{i+1}"
            structured['original_filename'] = f"simulated_voucher_{i+1}.pdf"
            simulated_vouchers.append(structured)
    logging.info(f"Simulated processing for {len(simulated_vouchers)} vouchers.")
    return simulated_vouchers


def main():
    parser = argparse.ArgumentParser(description="Headless Accounting System Batch Processor")
    parser.add_argument("--statements_path", type=str, help="Path to the bank statement CSV file or directory containing CSVs.")
    parser.add_argument("--accounts_config", type=str, default=DEFAULT_ACCOUNTS_PATH, help="Path to accounts.yml.")
    parser.add_argument("--rules_config", type=str, default=DEFAULT_RULES_PATH, help="Path to rules.yml.")
    parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory for output files.")
    parser.add_argument("--num_sim_vouchers", type=int, default=3, help="Number of vouchers to simulate for processing.")
    # parser.add_argument("--vouchers_dir", type=str, help="Path to directory containing voucher files (future use).")


    args = parser.parse_args()

    ensure_output_dir(args.output_dir)

    logging.info("Starting headless accounting batch process...")

    # 1. Load Configurations
    logging.info(f"Loading accounts from: {args.accounts_config}")
    accounts = load_accounts_config(args.accounts_config)
    if not accounts:
        logging.error("Failed to load accounts configuration. Exiting.")
        return

    logging.info(f"Loading rules from: {args.rules_config}")
    rules = load_rules_config(args.rules_config)
    if not rules: # Allow rules to be optional
        logging.warning("Rules configuration not loaded or empty. Proceeding without transaction rules.")
        rules = []

    # 2. Process Bank Statements
    all_statement_transactions = []
    if args.statements_path:
        if os.path.isfile(args.statements_path):
            logging.info(f"Parsing statement file: {args.statements_path}")
            statement_txs = parse_statement_csv(args.statements_path)
            for i, tx in enumerate(statement_txs):
                tx['id'] = f"stmt_{os.path.basename(args.statements_path)}_{i+1}"
            all_statement_transactions.extend(statement_txs)
        elif os.path.isdir(args.statements_path):
            logging.info(f"Parsing statement files from directory: {args.statements_path}")
            for filename in os.listdir(args.statements_path):
                if filename.lower().endswith(".csv"):
                    file_path = os.path.join(args.statements_path, filename)
                    logging.info(f"Parsing statement file: {file_path}")
                    statement_txs = parse_statement_csv(file_path)
                    for i, tx in enumerate(statement_txs):
                        tx['id'] = f"stmt_{filename}_{i+1}"
                    all_statement_transactions.extend(statement_txs)
        else:
            logging.error(f"Statements path is not a valid file or directory: {args.statements_path}")
            # Allow to proceed if other operations might still be valid (e.g. only voucher processing)
            # return # Optionally exit if statements are critical

        if not all_statement_transactions and args.statements_path: # only warn if a path was given but no tx found
            logging.warning("No statement transactions parsed from the provided path. Further processing might yield empty results.")
    else:
        logging.warning("No statements_path provided. Skipping statement processing.")

    # 3. Process Vouchers (Placeholder)
    logging.info(f"Simulating voucher processing for {args.num_sim_vouchers} vouchers...")
    processed_vouchers = process_vouchers_placeholder(args.num_sim_vouchers)
    if not processed_vouchers:
        logging.warning("No vouchers processed. Matching will likely result in all unmatched.")

    # 4. Perform Matching
    logging.info("Matching statement transactions to vouchers...")
    matched_data = match_transactions_to_vouchers(all_statement_transactions, processed_vouchers)
    logging.info(f"Matching complete. Processed {len(matched_data)} items (matched/unmatched/ignored).")

    # 5. Generate Journal Entries
    logging.info("Generating journal entries...")
    default_bank_account_name = "Checking Account"
    if accounts:
        asset_accounts = [acc.get("name") for acc in accounts if acc.get("type", "").lower() == "asset" and acc.get("name")]
        if asset_accounts:
            default_bank_account_name = asset_accounts[0]
    logging.info(f"Using '{default_bank_account_name}' as the default bank account for journal entries.")

    journal_entries = generate_journal_entries(matched_data, accounts, rules, default_bank_account_name=default_bank_account_name)
    logging.info(f"Generated {len(journal_entries)} journal entries.")

    je_output_path = os.path.join(args.output_dir, DEFAULT_JOURNAL_ENTRIES_FILENAME)
    try:
        import json
        def je_serializer(obj):
            if isinstance(obj, (datetime, date)): # Handle both datetime and date
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable for object: {obj}")

        with open(je_output_path, 'w', encoding='utf-8') as f:
            json.dump(journal_entries, f, indent=4, default=je_serializer)
        logging.info(f"Journal entries saved to: {je_output_path}")
    except Exception as e:
        logging.error(f"Failed to save journal entries to JSON: {e}")


    # 6. Generate Trial Balance
    logging.info("Generating trial balance...")
    tb_output_path = os.path.join(args.output_dir, DEFAULT_TRIAL_BALANCE_FILENAME)
    success, _ = generate_trial_balance(journal_entries, tb_output_path)
    if success:
        logging.info(f"Trial balance saved to: {tb_output_path}")
    else:
        logging.error("Failed to generate trial balance.")

    logging.info("Batch process completed.")


if __name__ == "__main__":
    # --- Setup for CLI testing ---
    if not os.path.exists(DEFAULT_ACCOUNTS_PATH):
        ensure_output_dir("config")
        with open(DEFAULT_ACCOUNTS_PATH, "w", encoding='utf-8') as f: # Added encoding
            f.write("accounts:\n  - name: Checking Account\n    type: Asset\n    identifier: '1234'\n  - name: Office Supplies\n    type: Expense\n")
        logging.info(f"Created dummy {DEFAULT_ACCOUNTS_PATH}")

    if not os.path.exists(DEFAULT_RULES_PATH):
        ensure_output_dir("config") # ensure_output_dir works for any path components
        with open(DEFAULT_RULES_PATH, "w", encoding='utf-8') as f: # Added encoding
            f.write("rules:\n  - name: 'Office Supplies Rule'\n    conditions: {keywords: ['office depot', 'staples']}\n    account: Office Supplies\n")
        logging.info(f"Created dummy {DEFAULT_RULES_PATH}")

    sample_statement_cli_path = "data/sample_statement_for_cli.csv"
    if not os.path.exists("data"):
        os.makedirs("data")
        logging.info("Created data directory for CLI sample statement.")
    if not os.path.exists(sample_statement_cli_path):
        with open(sample_statement_cli_path, 'w', newline='', encoding='utf-8') as sf:
            # csv was imported at the top
            writer = csv.writer(sf)
            writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])
            writer.writerow(["2023-11-01","OFFICE DEPOT STORE #999","50.00","",950.00])
            writer.writerow(["2023-11-05","Misc Deposit",,"200.00",1150.00])
        logging.info(f"Created dummy {sample_statement_cli_path}")

    # --- End of Setup for CLI testing ---

    main()
