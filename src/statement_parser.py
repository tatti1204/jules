import csv
from decimal import Decimal, InvalidOperation

def parse_statement_csv(file_path):
    """
    Parses a bank statement CSV file and returns a list of transactions.
    Expected CSV columns: Date, Description, Amount Debit, Amount Credit, Balance
    Assumes amounts are positive numbers. Debit decreases balance, Credit increases.
    Returns a list of dictionaries, each representing a transaction.
    """
    transactions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # Check for required headers (case-insensitive check)
            expected_headers = ["date", "description", "amount debit", "amount credit", "balance"]
            actual_headers_lower = [header.lower() for header in reader.fieldnames or []]

            missing_headers = [eh for eh in expected_headers if eh not in actual_headers_lower]
            if missing_headers:
                print(f"Error: Missing expected CSV headers: {', '.join(missing_headers)}")
                return []

            for row in reader:
                try:
                    # Normalize keys from the reader (e.g. "Amount Debit" -> "amount debit")
                    row_lower_keys = {k.lower(): v for k, v in row.items()}

                    date = row_lower_keys.get("date", "").strip()
                    description = row_lower_keys.get("description", "").strip()

                    debit_str = row_lower_keys.get("amount debit", "0").strip()
                    credit_str = row_lower_keys.get("amount credit", "0").strip()
                    balance_str = row_lower_keys.get("balance", "0").strip()

                    if not date or not description:
                        print(f"Warning: Skipping row due to missing date or description: {row}")
                        continue

                    amount = Decimal("0.00")
                    transaction_type = ""

                    if debit_str and debit_str != "0": # Ensure debit_str is not empty or "0"
                        amount = -abs(Decimal(debit_str)) # Debits are negative
                        transaction_type = "debit"
                    elif credit_str and credit_str != "0": # Ensure credit_str is not empty or "0"
                        amount = abs(Decimal(credit_str)) # Credits are positive
                        transaction_type = "credit"
                    else:
                        # Handle rows that might only have balance or are informational
                        if description.lower() == "initial balance":
                             # For initial balance, amount can be 0 if it's just setting the scene
                             # Or it could be considered a credit if that's how the balance starts
                             # For now, let amount be 0 and type be empty, balance is the key.
                            pass # Amount is 0, type is empty
                        elif not debit_str and not credit_str: # No monetary change
                            print(f"Info: Row with no debit/credit amount (e.g. balance check or info): {row}")
                            # We might still want to record this if it has a balance, but no amount/type
                            # For now, skip if not 'initial balance'
                            continue
                        # If one is "0" and the other is empty/missing, it's effectively handled by above conditions
                        # This 'else' might not be strictly necessary if above conditions are comprehensive

                    balance = Decimal(balance_str)

                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "type": transaction_type, # 'debit' or 'credit' or empty
                        "balance": balance
                    })
                except InvalidOperation as e:
                    print(f"Warning: Could not parse amount/balance for row: {row}. Error: {e}. Skipping.")
                except Exception as e:
                    print(f"Warning: Error processing row: {row}. Error: {e}. Skipping.")
    except FileNotFoundError:
        print(f"Error: Statement file {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error reading or processing CSV file {file_path}: {e}")
        return []

    return transactions

if __name__ == '__main__':
    # Create a dummy data directory if it doesn't exist for the example
    import os
    if not os.path.exists("data"):
        os.makedirs("data")

    sample_file_path = "data/sample_statement.csv"
    # Recreate the sample file for consistent testing during __main__ runs
    with open(sample_file_path, 'w', newline='', encoding='utf-8') as sf:
        writer = csv.writer(sf)
        writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])
        writer.writerow(["2023-10-01","Initial Balance","","",1000.00])
        writer.writerow(["2023-10-05","OFFICE DEPOT STORE #123","50.00","",950.00])
        writer.writerow(["2023-10-07","Salary Deposit","","500.00",1450.00])
        writer.writerow(["2023-10-10","ZOOM VIDEO COMMUNICATIONS","15.00","",1435.00])
        writer.writerow(["2023-10-12","TRANSFER FROM SAVINGS","","200.00",1635.00])
        writer.writerow(["2023-10-15","STAPLES #456","75.50","",1559.50]) # Ensure debit has value
        writer.writerow(["2023-10-18","Invalid Amount Row","invalid","",1500.00])
        writer.writerow(["2023-10-19","Missing Date","","10.00","",1490.00]) # Credit amount here
        writer.writerow(["2023-10-20","No Amount Row","","",1490.00])


    print(f"Parsing statement: {sample_file_path}")
    parsed_transactions = parse_statement_csv(sample_file_path)

    if parsed_transactions:
        print("\nParsed Transactions:")
        for t in parsed_transactions:
            print(f"  Date: {t['date']}, Desc: {t['description']}, Amount: {t['amount']}, Type: {t['type']}, Balance: {t['balance']}")
    else:
        print("No transactions were parsed or an error occurred.")

    print("\nTesting with a non-existent file:")
    non_existent = parse_statement_csv("data/non_existent_statement.csv")
    if not non_existent:
        print("Correctly handled non-existent file.")

    print("\nTesting with a CSV with missing headers:")
    missing_header_path = "data/missing_header_statement.csv"
    with open(missing_header_path, 'w', newline='', encoding='utf-8') as mhf:
        writer = csv.writer(mhf)
        writer.writerow(["Date","Description","Amount Debit","Balance"]) # Missing "Amount Credit"
        writer.writerow(["2023-10-01","Test","10","","100"]) # Added empty string for missing credit, assuming balance is the last intended value
    missing_header_trans = parse_statement_csv(missing_header_path)
    if not missing_header_trans:
        print("Correctly handled missing headers.")
    if os.path.exists(missing_header_path):
        os.remove(missing_header_path)

    # Clean up the main sample file created in __main__ if it's in the root data folder
    # This is to avoid interference with tests if they also use this exact path,
    # though tests should ideally use their own temporary, isolated files.
    # if os.path.exists(sample_file_path):
    #     os.remove(sample_file_path)
    # if os.path.exists("data/missing_header_statement.csv"): # ensure cleanup
    #    os.remove("data/missing_header_statement.csv")
    # if os.path.exists("data") and not os.listdir("data"): # remove data dir if empty and created by main
    #    os.rmdir("data")
