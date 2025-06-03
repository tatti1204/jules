from datetime import date
from decimal import Decimal

def apply_rules_to_transaction(transaction_description, transaction_amount, rules_config):
    """
    Applies configured rules to a transaction to determine the expense account.
    Rules are checked in order; the first matching rule is applied.
    Args:
        transaction_description (str): The description from the statement or voucher.
        transaction_amount (Decimal): The amount of the transaction.
        rules_config (list): A list of rule dictionaries from rules.yml.
    Returns:
        dict: The rule that matched, or None if no rule matched.
    """
    if not rules_config or not transaction_description:
        return None

    desc_lower = transaction_description.lower()

    for rule in rules_config:
        conditions = rule.get("conditions", {})
        keywords = conditions.get("keywords", [])
        # amount_min = conditions.get("amount_min") # Not implemented in this version
        # amount_max = conditions.get("amount_max") # Not implemented in this version

        if not keywords: # Rule must have keywords to be considered for matching
            continue

        # Check if any keyword from the rule is present in the transaction description
        if any(keyword.lower() in desc_lower for keyword in keywords):
            # Further condition checks like amount range could be added here
            return rule
    return None

def generate_journal_entries(matched_results, accounts_config, rules_config, default_bank_account_name="Checking Account", default_suspense_account_name="Suspense"):
    """
    Generates journal entries from matched statement/voucher pairs and unmatched transactions.

    Args:
        matched_results (list): Output from match_transactions_to_vouchers. Each item is a dict
                               with 'statement', 'voucher' (optional), and 'status'.
        accounts_config (list): Loaded accounts.yml data.
        rules_config (list): Loaded rules.yml data.
        default_bank_account_name (str): Name of the primary bank account to use if not specified.
        default_suspense_account_name (str): Account for unclassified transactions.

    Returns:
        list: A list of journal entry dictionaries.
    """
    journal_entries = []

    bank_account_details = next((acc for acc in accounts_config if acc.get('name') == default_bank_account_name), None)
    if not bank_account_details:
        print(f"Warning: Default bank account '{default_bank_account_name}' not found in accounts.yml. Using fallback name and assuming 'Asset' type.")
        bank_account_name = default_bank_account_name
        # bank_account_type = 'Asset' # Assuming Asset, this might need to be more robust
    else:
        bank_account_name = bank_account_details.get('name')
        # bank_account_type = bank_account_details.get('type')


    for item in matched_results:
        statement_tx = item.get("statement")
        voucher = item.get("voucher")
        status = item.get("status")

        if not statement_tx:
            continue

        tx_date_str = statement_tx.get("date")
        tx_date_obj = None
        if isinstance(tx_date_str, date):
            tx_date_obj = tx_date_str
        elif isinstance(tx_date_str, str):
            try:
                tx_date_obj = date.fromisoformat(tx_date_str)
            except ValueError:
                print(f"Warning: Invalid date format for statement: {tx_date_str}. Skipping entry.")
                continue
        else:
            print(f"Warning: Invalid or missing date for statement: {tx_date_str}. Skipping entry.")
            continue

        tx_amount = statement_tx.get("amount", Decimal(0))
        tx_description = statement_tx.get("description", "N/A")

        entry_description = tx_description
        # Use voucher vendor name if available and status is matched, for better description
        if voucher and voucher.get('vendor_name') and status == "matched":
            entry_description = f"{voucher.get('vendor_name')} - {tx_description}"


        entry = {
            "date": tx_date_obj.isoformat(),
            "description": entry_description,
            "postings": [],
            "status": "needs_review",
            "source_statement_id": statement_tx.get("id"),
            "source_voucher_id": voucher.get("id") if voucher else None
        }

        if status == "matched" and voucher:
            # Use voucher's raw_text or vendor_name for rule application if available
            rule_source_description = voucher.get("raw_text") or voucher.get("vendor_name")
            rule = apply_rules_to_transaction(rule_source_description, voucher.get("total_amount"), rules_config)

            expense_account_name = default_suspense_account_name
            if rule and rule.get("account"):
                expense_account_name = rule.get("account")
                entry["status"] = "auto_generated_rule"
            else:
                entry["status"] = "auto_generated_matched_no_rule"

            abs_tx_amount = abs(tx_amount)
            entry["postings"].append({"account": expense_account_name, "debit": abs_tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": bank_account_name, "debit": Decimal(0), "credit": abs_tx_amount})

        elif status == "unmatched" and tx_amount < Decimal(0):
            abs_tx_amount = abs(tx_amount)
            entry["postings"].append({"account": default_suspense_account_name, "debit": abs_tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": bank_account_name, "debit": Decimal(0), "credit": abs_tx_amount})
            entry["status"] = "unmatched_debit"

        elif status == "ignored_credit_or_zero" and tx_amount > Decimal(0):
            rule = apply_rules_to_transaction(tx_description, tx_amount, rules_config)

            income_account_name = default_suspense_account_name
            if rule and rule.get("account"):
                income_account_name = rule.get("account")
                entry["status"] = "auto_generated_rule_income"
            else:
                entry["status"] = "unmatched_credit"

            entry["postings"].append({"account": bank_account_name, "debit": tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": income_account_name, "debit": Decimal(0), "credit": tx_amount})

        else:
            if tx_amount != Decimal(0): # Log only if it's non-zero and unhandled
                 print(f"Info: Skipping journal entry for statement '{tx_description}' with amount {tx_amount} and status '{status}'.")
            continue

        if entry["postings"]:
            journal_entries.append(entry)

    return journal_entries

if __name__ == '__main__':
    # Sample configurations (replace with actual loading in a real app)
    sample_accounts = [
        {"name": "Checking Account", "type": "Asset"},
        {"name": "Office Supplies", "type": "Expense"},
        {"name": "Software Subscriptions", "type": "Expense"},
        {"name": "Sales Revenue", "type": "Revenue"},
        {"name": "Suspense", "type": "Equity"} # Or Asset/Liability depending on convention
    ]
    sample_rules = [
        {"name": "Office Supplies Rule", "conditions": {"keywords": ["office depot", "staples"]}, "account": "Office Supplies"},
        {"name": "Zoom Rule", "conditions": {"keywords": ["zoom video", "zoom.us"]}, "account": "Software Subscriptions"},
        {"name": "Generic Income Rule", "conditions": {"keywords": ["deposit", "client payment"]}, "account": "Sales Revenue"}
    ]

    # Sample matched_results from matching_engine
    sample_matched_results = [
        {
            "statement": {'id': 'stmt1', 'date': date(2023, 10, 5), 'description': 'OFFICE DEPOT #123', 'amount': Decimal('-50.00')},
            "voucher": {'id': 'vouch1', 'vendor_name': 'Office Depot', 'transaction_date': date(2023, 10, 4), 'total_amount': Decimal('50.00'), 'raw_text': 'Office Depot receipt...'},
            "status": "matched"
        },
        {
            "statement": {'id': 'stmt2', 'date': date(2023, 10, 10), 'description': 'ZOOM.US QWERTY', 'amount': Decimal('-15.00')},
            "voucher": {'id': 'vouch2', 'vendor_name': 'Zoom Video Communications', 'transaction_date': date(2023, 10, 9), 'total_amount': Decimal('15.00'), 'raw_text': 'Zoom.us invoice...'},
            "status": "matched"
        },
        {
            "statement": {'id': 'stmt3', 'date': date(2023, 10, 15), 'description': 'UNKNOWN VENDOR PAYMENT', 'amount': Decimal('-75.50')},
            "voucher": None,
            "status": "unmatched"
        },
        {
            "statement": {'id': 'stmt4', 'date': date(2023, 10, 12), 'description': 'MICROSOFT 365', 'amount': Decimal('-9.99')},
            "voucher": {'id': 'vouch3', 'vendor_name': 'Microsoft', 'transaction_date': date(2023, 10, 12), 'total_amount': Decimal('9.99'), 'raw_text': 'Microsoft 365 subscription'},
            "status": "matched" # This will go to Suspense as no "Microsoft" rule defined in sample_rules
        },
        {
            "statement": {'id': 'stmt5', 'date': date(2023, 10, 20), 'description': 'Client Payment ABC Corp', 'amount': Decimal('1200.00')},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        },
        { # Zero amount transaction example
            "statement": {'id': 'stmt6', 'date': date(2023,10,22), 'description': 'Zero amount test', 'amount': Decimal('0.00')},
            "voucher": None,
            "status": "ignored_credit_or_zero" # Or any other status if it's zero
        }
    ]

    print("--- Generating Journal Entries ---")
    generated_entries = generate_journal_entries(sample_matched_results, sample_accounts, sample_rules)

    for i, entry in enumerate(generated_entries):
        print(f"\n--- Journal Entry {i+1} ---")
        print(f"Date: {entry['date']}")
        print(f"Description: {entry['description']}")
        print(f"Status: {entry['status']}")
        print("Postings:")
        for p in entry['postings']:
            print(f"  Account: {p['account']}, Debit: {p['debit']}, Credit: {p['credit']}")

    print("\n--- Test with default bank not in config ---")
    generated_entries_alt_bank = generate_journal_entries(
        [sample_matched_results[0]], # Just one transaction
        sample_accounts,
        sample_rules,
        default_bank_account_name="My Other Bank"
    )
    if generated_entries_alt_bank:
        print(f"Date: {generated_entries_alt_bank[0]['date']}")
        print(f"Description: {generated_entries_alt_bank[0]['description']}")
        print("Postings for alternative bank:")
        for p in generated_entries_alt_bank[0]['postings']:
            print(f"  Account: {p['account']}, Debit: {p['debit']}, Credit: {p['credit']}")
    else:
        print("No entries generated for alternative bank test.")
