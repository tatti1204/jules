from datetime import date
from decimal import Decimal

# apply_rules_to_transaction function remains the same

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
    Generates journal entries from matched statement/voucher pairs and unmatched transactions,
    including a confidence score and more granular status.
    """
    journal_entries = []

    bank_account_details = next((acc for acc in accounts_config if acc.get('name') == default_bank_account_name), None)
    if not bank_account_details:
        print(f"Warning: Default bank account '{default_bank_account_name}' not found in accounts.yml. Using fallback name and assuming 'Asset' type.")
        bank_account_name = default_bank_account_name
    else:
        bank_account_name = bank_account_details.get('name')


    for item_idx, item in enumerate(matched_results): # Added index for potential unique ID generation
        statement_tx = item.get("statement")
        voucher = item.get("voucher")
        status_from_matcher = item.get("status")

        if not statement_tx:
            continue

        tx_date_str = statement_tx.get("date")
        tx_date_obj = None
        if isinstance(tx_date_str, date):
            tx_date_obj = tx_date_str
        elif isinstance(tx_date_str, str):
            try:
                tx_date_obj = date.fromisoformat(tx_date_str)
            except ValueError as e: # Catch specific error
                print(f"Warning: Invalid date format for statement: {tx_date_str} ({e}). Skipping entry.")
                continue
        else:
            print(f"Warning: Invalid or missing date ({tx_date_str}) for statement dated {statement_tx.get('original_date_if_any', 'N/A')}. Skipping entry.") # Added more context if original date was stored
            continue

        tx_amount = statement_tx.get("amount", Decimal(0))
        tx_description = statement_tx.get("description", "N/A")

        entry_description = tx_description
        if voucher and voucher.get('vendor_name'):
            if voucher.get('vendor_name','').lower() not in tx_description.lower():
                 entry_description = f"{voucher.get('vendor_name')} - {tx_description}"
            # else: vendor name already in description, no change needed.


        # Initialize status and confidence
        current_status = "needs_review_low_confidence" # A more generic default
        confidence_score = Decimal("0.1") # Default low confidence
        entry_notes = ""


        entry = {
            "id": statement_tx.get("id", f"je_gen_{item_idx+1}"),
            "date": tx_date_obj.isoformat(),
            "description": entry_description,
            "postings": [],
            "status": current_status, # Will be updated
            "confidence_score": confidence_score, # Will be updated
            "source_statement_id": statement_tx.get("id"),
            "source_voucher_id": voucher.get("id") if voucher else None,
            "notes": entry_notes
        }

        if status_from_matcher == "matched" and voucher:
            rule_text_source = voucher.get("raw_text") or voucher.get("vendor_name")
            rule = apply_rules_to_transaction(rule_text_source, voucher.get("total_amount"), rules_config)

            expense_account_name = default_suspense_account_name
            if rule and rule.get("account"):
                expense_account_name = rule.get("account")
                current_status = "auto_generated_high_confidence"
                confidence_score = Decimal("0.9")
            else:
                current_status = "needs_review_matched_no_rule"
                confidence_score = Decimal("0.6")
                entry_notes = "Voucher matched to statement, but no specific rule found for GL account."


            abs_tx_amount = abs(tx_amount)
            entry["postings"].append({"account": expense_account_name, "debit": abs_tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": bank_account_name, "debit": Decimal(0), "credit": abs_tx_amount})

        elif status_from_matcher == "unmatched" and tx_amount < Decimal(0):
            abs_tx_amount = abs(tx_amount)
            entry["postings"].append({"account": default_suspense_account_name, "debit": abs_tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": bank_account_name, "debit": Decimal(0), "credit": abs_tx_amount})
            current_status = "needs_review_unmatched_debit"
            confidence_score = Decimal("0.3")
            entry_notes = "Statement debit transaction with no matching voucher."

        elif status_from_matcher == "ignored_credit_or_zero" and tx_amount > Decimal(0):
            rule = apply_rules_to_transaction(tx_description, tx_amount, rules_config)

            income_account_name = default_suspense_account_name
            if rule and rule.get("account"):
                income_account_name = rule.get("account")
                current_status = "auto_generated_income_high_confidence"
                confidence_score = Decimal("0.8")
            else:
                current_status = "needs_review_unmatched_credit"
                confidence_score = Decimal("0.5")
                entry_notes = "Statement credit transaction with no specific rule for GL account."

            entry["postings"].append({"account": bank_account_name, "debit": tx_amount, "credit": Decimal(0)})
            entry["postings"].append({"account": income_account_name, "debit": Decimal(0), "credit": tx_amount})

        else:
            if tx_amount != Decimal(0):
                 print(f"Info: Skipping journal entry for statement '{tx_description}' with amount {tx_amount} and matcher status '{status_from_matcher}'.")
            continue

        entry["status"] = current_status
        entry["confidence_score"] = confidence_score
        entry["notes"] = entry_notes

        if entry["postings"]:
            journal_entries.append(entry)

    return journal_entries

# __main__ block from previous version, might need minor adjustments for new statuses/fields if run directly
if __name__ == '__main__':
    sample_accounts = [
        {"name": "Checking Account", "type": "Asset"},
        {"name": "Office Supplies", "type": "Expense"},
        {"name": "Software Subscriptions", "type": "Expense"},
        {"name": "Sales Revenue", "type": "Revenue"},
        {"name": "Suspense", "type": "Equity"}
    ]
    sample_rules = [
        {"name": "Office Supplies Rule", "conditions": {"keywords": ["office depot", "staples"]}, "account": "Office Supplies"},
        {"name": "Zoom Rule", "conditions": {"keywords": ["zoom video", "zoom.us"]}, "account": "Software Subscriptions"},
        {"name": "Generic Income Rule", "conditions": {"keywords": ["deposit", "client payment"]}, "account": "Sales Revenue"}
    ]

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
            "status": "matched"
        },
        {
            "statement": {'id': 'stmt5', 'date': date(2023, 10, 20), 'description': 'Client Payment ABC Corp', 'amount': Decimal('1200.00')},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        },
        {
            "statement": {'id': 'stmt6', 'date': date(2023,10,22), 'description': 'Zero amount test', 'amount': Decimal('0.00')},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        }
    ]

    print("--- Generating Journal Entries (with new status/confidence) ---")
    generated_entries = generate_journal_entries(sample_matched_results, sample_accounts, sample_rules)

    for i, entry in enumerate(generated_entries):
        print(f"\n--- Journal Entry {i+1} ---")
        print(f"ID: {entry['id']}")
        print(f"Date: {entry['date']}")
        print(f"Description: {entry['description']}")
        print(f"Status: {entry['status']}")
        print(f"Confidence: {entry['confidence_score']}")
        print(f"Notes: {entry['notes']}")
        print("Postings:")
        for p in entry['postings']:
            print(f"  Account: {p['account']}, Debit: {p['debit']}, Credit: {p['credit']}")
