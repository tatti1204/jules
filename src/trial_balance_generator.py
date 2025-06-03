import csv
from collections import defaultdict
from decimal import Decimal

def generate_trial_balance(journal_entries, output_csv_path="data/trial_balance.csv"):
    """
    Generates a trial balance from a list of journal entries and saves it to a CSV file.

    Args:
        journal_entries (list): A list of journal entry dictionaries.
                                Each entry must have a 'postings' key, which is a list of dicts,
                                each with 'account', 'debit' (Decimal), and 'credit' (Decimal).
        output_csv_path (str): The path to save the generated CSV file.

    Returns:
        bool: True if generation and saving were successful, False otherwise.
        dict: A dictionary representing the trial balance totals {account: {'debit': Decimal, 'credit': Decimal}}
    """
    if not journal_entries:
        print("Warning: No journal entries provided to generate trial balance.")
        # Still create an empty CSV with headers for consistency
        try:
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Account Name", "Total Debit", "Total Credit"])
                # For an empty set of entries, a GRAND TOTAL of 0,0 is appropriate.
                writer.writerow(["GRAND TOTAL", Decimal("0"), Decimal("0")])
            return True, {} # Success in writing empty file
        except IOError as e:
            print(f"Error writing empty trial balance CSV to {output_csv_path}: {e}")
            return False, {}


    account_totals = defaultdict(lambda: {"debit": Decimal(0), "credit": Decimal(0)})

    for entry in journal_entries:
        postings = entry.get("postings", [])
        if not postings:
            print(f"Warning: Journal entry dated {entry.get('date', 'N/A')} has no postings. Skipping.")
            continue

        entry_total_debit = Decimal(0)
        entry_total_credit = Decimal(0)

        valid_postings_for_entry = []
        for p_idx, posting_raw in enumerate(postings):
            account_name = posting_raw.get("account")
            debit_amount_raw = posting_raw.get("debit", Decimal(0))
            credit_amount_raw = posting_raw.get("credit", Decimal(0))

            if not account_name:
                print(f"Warning: Posting #{p_idx+1} in entry dated {entry.get('date', 'N/A')} has no account name. Skipping posting.")
                continue # Skip this specific posting

            try:
                debit_amount = Decimal(str(debit_amount_raw)) if not isinstance(debit_amount_raw, Decimal) else debit_amount_raw
            except Exception:
                print(f"Warning: Invalid debit amount '{debit_amount_raw}' for account '{account_name}' in entry dated {entry.get('date', 'N/A')}. Using 0.")
                debit_amount = Decimal(0)

            try:
                credit_amount = Decimal(str(credit_amount_raw)) if not isinstance(credit_amount_raw, Decimal) else credit_amount_raw
            except Exception:
                print(f"Warning: Invalid credit amount '{credit_amount_raw}' for account '{account_name}' in entry dated {entry.get('date', 'N/A')}. Using 0.")
                credit_amount = Decimal(0)

            valid_postings_for_entry.append({
                "account": account_name, "debit": debit_amount, "credit": credit_amount
            })
            entry_total_debit += debit_amount
            entry_total_credit += credit_amount

        if entry_total_debit != entry_total_credit:
            print(f"Warning: Journal entry dated {entry.get('date', 'N/A')} (Desc: {entry.get('description', 'N/A')}) is unbalanced. Debits: {entry_total_debit}, Credits: {entry_total_credit}. Still processing valid postings.")

        # Process valid postings from this entry
        for posting in valid_postings_for_entry:
            account_totals[posting["account"]]["debit"] += posting["debit"]
            account_totals[posting["account"]]["credit"] += posting["credit"]

    # If all entries/postings were invalid or skipped, account_totals might be empty.
    # Handle this similar to empty journal_entries input.
    if not account_totals:
        print("Warning: No valid postings found in journal entries to generate trial balance lines.")
        try:
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Account Name", "Total Debit", "Total Credit"])
                writer.writerow(["GRAND TOTAL", Decimal("0"), Decimal("0")])
            return True, {}
        except IOError as e:
            print(f"Error writing trial balance CSV with only totals to {output_csv_path}: {e}")
            return False, {}

    sorted_accounts = sorted(account_totals.items())

    try:
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Account Name", "Total Debit", "Total Credit"])
            grand_total_debit = Decimal(0)
            grand_total_credit = Decimal(0)
            for account_name, totals in sorted_accounts:
                writer.writerow([account_name, totals["debit"], totals["credit"]])
                grand_total_debit += totals["debit"]
                grand_total_credit += totals["credit"]
            writer.writerow(["GRAND TOTAL", grand_total_debit, grand_total_credit])

        print(f"Trial balance successfully generated and saved to {output_csv_path}")
        if grand_total_debit != grand_total_credit:
            print(f"CRITICAL WARNING: The trial balance is unbalanced! Total Debits: {grand_total_debit}, Total Credits: {grand_total_credit}")
        else:
            print(f"Trial balance is balanced. Total Debits/Credits: {grand_total_debit}")

        return True, dict(account_totals)
    except IOError as e:
        print(f"Error writing trial balance CSV to {output_csv_path}: {e}")
        return False, dict(account_totals)


if __name__ == '__main__':
    sample_journal_entries_tb = [
        {
            "date": "2023-10-05", "description": "Office Supplies Purchase",
            "postings": [
                {"account": "Office Supplies", "debit": Decimal("50.00"), "credit": Decimal("0")},
                {"account": "Checking Account", "debit": Decimal("0"), "credit": Decimal("50.00")}
            ]
        },
        {
            "date": "2023-10-10", "description": "Software Subscription",
            "postings": [
                {"account": "Software Subscriptions", "debit": Decimal("15.00"), "credit": Decimal("0")},
                {"account": "Checking Account", "debit": Decimal("0"), "credit": Decimal("15.00")}
            ]
        },
        {
            "date": "2023-10-11", "description": "Partial Payment (Unbalanced)",
            "postings": [
                {"account": "Accounts Payable", "debit": Decimal("0"), "credit": Decimal("100.00")},
                {"account": "Cash", "debit": Decimal("90.00"), "credit": Decimal("0")}
            ]
        },
        {
            "date": "2023-10-20", "description": "Sales Revenue",
            "postings": [
                {"account": "Checking Account", "debit": Decimal("1200.00"), "credit": Decimal("0")},
                {"account": "Sales Revenue", "debit": Decimal("0"), "credit": Decimal("1200.00")}
            ]
        },
        {
            "date": "2023-10-22", "description": "Miscellaneous Expense",
            "postings": [
                {"account": "Miscellaneous Expense", "debit": "25.75", "credit": "0.00"},
                {"account": "Checking Account", "debit": "0.00", "credit": "25.75"}
            ]
        }
    ]
    import os
    if not os.path.exists("data"):
        os.makedirs("data")

    print("--- Generating Trial Balance from Sample Entries ---")
    success, totals = generate_trial_balance(sample_journal_entries_tb, "data/sample_trial_balance.csv")
    if success:
        print("Sample trial_balance.csv generated.")
    else:
        print("Failed to generate sample trial_balance.csv.")

    print("\n--- Test with empty journal entries ---")
    success_empty, _ = generate_trial_balance([], "data/empty_trial_balance.csv")
    if success_empty:
        print("Empty trial_balance.csv generated.")

    print("\n--- Test with entry having no postings ---")
    entries_with_empty_posting = [{"date": "2023-11-01", "description": "Empty Posting Entry", "postings": []}]
    generate_trial_balance(entries_with_empty_posting, "data/trial_balance_with_empty_posting.csv")

    print("\n--- Test with entry having only invalid postings ---")
    entries_with_invalid_postings = [{
        "date": "2023-11-02", "description": "Invalid Postings Only",
        "postings": [
            {"account": None, "debit": "10", "credit": "0"}, # No account
            {"account": "BadAmount", "debit": "ABC", "credit": "0"} # Bad amount
        ]
    }]
    generate_trial_balance(entries_with_invalid_postings, "data/trial_balance_invalid_postings.csv")
