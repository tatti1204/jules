from datetime import timedelta, date
from decimal import Decimal

def find_matching_voucher(statement_transaction, available_vouchers, date_tolerance_days=3):
    """
    Finds a matching voucher for a given bank statement transaction.

    Args:
        statement_transaction (dict): A dictionary representing a parsed bank statement transaction.
                                   Expected keys: 'date' (string YYYY-MM-DD or date object),
                                                  'amount' (Decimal, negative for debits),
                                                  'description' (string).
        available_vouchers (list): A list of structured voucher dictionaries.
                                  Expected keys: 'transaction_date' (date object),
                                                 'total_amount' (Decimal, always positive),
                                                 'vendor_name' (string).
        date_tolerance_days (int): Number of days allowed for date difference.

    Returns:
        dict: The best matching voucher, or None if no suitable match is found.
              Modifies the matched voucher in available_vouchers by adding a '_matched' flag.
    """
    if not statement_transaction or not available_vouchers:
        return None

    # Convert statement transaction date string to date object if necessary
    st_date_str = statement_transaction.get('date')
    st_amount = statement_transaction.get('amount') # Should be Decimal
    st_description = statement_transaction.get('description', '').lower()

    if isinstance(st_date_str, str):
        try:
            st_date = date.fromisoformat(st_date_str)
        except ValueError:
            print(f"Warning: Invalid date format in statement transaction: {st_date_str}")
            return None
    elif isinstance(st_date_str, date):
        st_date = st_date_str
    else:
        print("Warning: Statement transaction date is missing or invalid type.")
        return None

    if st_amount is None: # Amount must exist
        print("Warning: Statement transaction amount is missing.")
        return None

    # Statement amounts are often negative for debits (expenses). Vouchers are positive.
    # We match absolute values, but only if statement_amount is negative (expense)
    if st_amount >= Decimal(0): # Only try to match expenses (debits) from statement
        return None


    potential_matches = []
    for voucher in available_vouchers:
        if voucher.get('_matched'): # Skip already matched vouchers
            continue

        v_date = voucher.get('transaction_date') # Should be date object
        v_amount = voucher.get('total_amount') # Should be Decimal, positive
        v_vendor = voucher.get('vendor_name', '').lower()

        if not isinstance(v_date, date) or v_amount is None:
            print(f"Warning: Skipping invalid voucher: {voucher.get('vendor_name')}")
            continue

        # 1. Amount Match (absolute values)
        # We expect statement debits (st_amount < 0) to match positive voucher totals.
        if abs(st_amount) != v_amount:
            continue

        # 2. Date Match (within tolerance)
        date_diff = abs((st_date - v_date).days)
        if date_diff > date_tolerance_days:
            continue

        # If we reach here, it's a potential match based on amount and date.
        # Score based on date proximity and description keyword match.
        score = 0

        # Score for date proximity (higher score for smaller difference)
        score += (date_tolerance_days - date_diff) * 10 # Max score date_tolerance_days * 10

        # Score for vendor name in description (simple check)
        if v_vendor and v_vendor in st_description:
            score += 50 # Significant bonus if vendor name matches

        # Consider other keywords if vendor name is generic or missing
        elif v_vendor: # Check parts of vendor name if full match fails
            vendor_parts = [part for part in v_vendor.split() if len(part) > 2]
            common_parts = sum(1 for part in vendor_parts if part in st_description)
            score += common_parts * 10


        if score > 0: # Only consider if there's some positive indication
            potential_matches.append({"voucher": voucher, "score": score, "date_diff": date_diff})

    if not potential_matches:
        return None

    # Sort by score (descending), then by date difference (ascending)
    potential_matches.sort(key=lambda x: (-x["score"], x["date_diff"]))

    best_match = potential_matches[0]["voucher"]
    # print(f"Debug: Matched STMT '{st_description}' ({st_amount} on {st_date}) to VOUCHER '{best_match.get('vendor_name')}' ({best_match.get('total_amount')} on {best_match.get('transaction_date')}) with score {potential_matches[0]['score']}")
    return best_match


def match_transactions_to_vouchers(statement_transactions, vouchers, date_tolerance_days=3):
    """
    Matches a list of statement transactions to a list of available vouchers.

    Args:
        statement_transactions (list): List of parsed statement transaction dicts.
        vouchers (list): List of structured voucher dicts.
        date_tolerance_days (int): Date tolerance for matching.

    Returns:
        list: A list of tuples, where each tuple is (statement_transaction, matched_voucher).
              If a statement transaction has no match, matched_voucher will be None.
              Vouchers that are matched will have a '_matched': True attribute set.
    """
    # Reset any prior match state on vouchers
    for v in vouchers:
        v['_matched'] = False

    matches = []
    # No need for unmatched_transactions list as per return type change in prompt
    # unmatched_transactions = []

    # Create a mutable list of vouchers to allow marking them as matched
    # The passed 'vouchers' list itself will be modified due to object references.
    # If the caller wants to preserve the original list of vouchers without '_matched' flags,
    # they should pass a deep copy. For this function, we work directly on the provided list.
    available_vouchers = vouchers

    for st_transaction in statement_transactions:
        if st_transaction.get('amount', Decimal(0)) >= Decimal(0):
            matches.append({"statement": st_transaction, "voucher": None, "status": "ignored_credit_or_zero"})
            continue

        matched_voucher = find_matching_voucher(st_transaction, available_vouchers, date_tolerance_days)

        if matched_voucher:
            matched_voucher['_matched'] = True # Mark voucher as used
            matches.append({"statement": st_transaction, "voucher": matched_voucher, "status": "matched"})
        else:
            matches.append({"statement": st_transaction, "voucher": None, "status": "unmatched"})
            # unmatched_transactions.append(st_transaction) # Not needed due to return type change

    return matches

if __name__ == '__main__':
    from datetime import date # Ensure date is imported here for sample data

    # Sample Data (ensure amounts are Decimal)
    sample_statements = [
        {'date': date(2023, 10, 5), 'description': 'OFFICE DEPOT #123', 'amount': Decimal('-50.00')},
        {'date': date(2023, 10, 10), 'description': 'ZOOM VIDEO US', 'amount': Decimal('-15.00')},
        {'date': date(2023, 10, 15), 'description': 'STAPLES STORE R US', 'amount': Decimal('-75.50')},
        {'date': date(2023, 10, 20), 'description': 'TRANSFER TO SAVINGS', 'amount': Decimal('-100.00')}, # No matching voucher
        {'date': date(2023, 10, 25), 'description': 'AMAZON PRIME VIDEO', 'amount': Decimal('-9.99')}, # Close date, diff amount for MSFT
        {'date': date(2023, 10, 7), 'description': 'SALARY DEPOSIT', 'amount': Decimal('1500.00')}, # Credit, should be ignored
        {'date': date(2023, 10, 28), 'description': 'UNKNOWN VENDOR PAYMENT', 'amount': Decimal('-30.00')} # Date match, no keyword for Generic
    ]

    sample_vouchers = [
        {'vendor_name': 'Office Depot', 'transaction_date': date(2023, 10, 4), 'total_amount': Decimal('50.00'), 'raw_text': '...'},
        {'vendor_name': 'Zoom Video Communications', 'transaction_date': date(2023, 10, 9), 'total_amount': Decimal('15.00'), 'raw_text': '...'},
        {'vendor_name': 'Staples', 'transaction_date': date(2023, 10, 16), 'total_amount': Decimal('75.50'), 'raw_text': '...'},
        {'vendor_name': 'Microsoft', 'transaction_date': date(2023, 10, 23), 'total_amount': Decimal('9.99'), 'raw_text': '...'},
        {'vendor_name': 'Generic Supplies Inc', 'transaction_date': date(2023, 10, 27), 'total_amount': Decimal('30.00'), 'raw_text': '...'}
    ]

    print("--- Running Matching Logic ---")
    all_matches = match_transactions_to_vouchers(sample_statements, sample_vouchers, date_tolerance_days=3)

    for m in all_matches:
        st = m['statement']
        vo = m['voucher']
        status = m['status']
        if status == "matched" and vo:
            print(f"MATCHED: '{st['description']}' ({st['amount']} on {st['date']})  ==> '{vo['vendor_name']}' ({vo['total_amount']} on {vo['transaction_date']})")
        elif status == "unmatched":
            print(f"UNMATCHED: '{st['description']}' ({st['amount']} on {st['date']})")
        elif status == "ignored_credit_or_zero":
            print(f"IGNORED (Credit/Zero): '{st['description']}' ({st['amount']} on {st['date']})")


    print("\n--- Checking voucher states ---")
    for v_idx, v in enumerate(sample_vouchers):
        print(f"Voucher {v_idx+1} ('{v['vendor_name']}'): Matched = {v.get('_matched', False)}")

    print("\n--- Test Case: No Vouchers ---")
    no_voucher_matches = match_transactions_to_vouchers(sample_statements, [], date_tolerance_days=3)
    unmatched_count = sum(1 for m_item in no_voucher_matches if m_item['status'] == 'unmatched')
    debit_statement_count = sum(1 for st_item in sample_statements if st_item['amount'] < Decimal(0))
    print(f"Unmatched transactions when no vouchers: {unmatched_count} (should be count of debits: {debit_statement_count})")


    print("\n--- Test Case: Voucher used only once ---")
    # Statement has two identical transactions, but only one voucher
    statements_double = [
        {'date': date(2023, 11, 1), 'description': 'COFFEE SHOP A', 'amount': Decimal('-5.00')},
        {'date': date(2023, 11, 2), 'description': 'COFFEE SHOP A', 'amount': Decimal('-5.00')}
    ]
    vouchers_single = [
        {'vendor_name': 'Coffee Shop A', 'transaction_date': date(2023, 11, 1), 'total_amount': Decimal('5.00')}
    ]
    double_matches = match_transactions_to_vouchers(statements_double, vouchers_single)
    matched_count_double = sum(1 for m_item in double_matches if m_item['status'] == 'matched')
    print(f"Matches for double transaction, single voucher: {matched_count_double} (should be 1)")
    # The following assertion would fail if __main__ was run by unittest, so it's for visual check or direct run.
    # self.assertTrue(any(v.get('_matched') for v in vouchers_single))
    if not any(v.get('_matched') for v in vouchers_single):
        print("Error: Expected voucher to be marked as matched in 'Voucher used only once' test.")
    elif matched_count_double != 1:
        print(f"Error: Matched count was {matched_count_double}, expected 1 in 'Voucher used only once' test.")
    else:
        print("Correctly handled 'Voucher used only once' scenario.")
