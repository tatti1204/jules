import unittest
import os
import csv
from decimal import Decimal
from src.statement_parser import parse_statement_csv

class TestStatementParser(unittest.TestCase):

    def setUp(self):
        self.test_data_dir = "tests/temp_data"
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.sample_csv_path = os.path.join(self.test_data_dir, "sample.csv")
        self.empty_csv_path = os.path.join(self.test_data_dir, "empty.csv")
        self.malformed_csv_path = os.path.join(self.test_data_dir, "malformed.csv")
        self.missing_headers_csv_path = os.path.join(self.test_data_dir, "missing_headers.csv")
        self.no_amount_csv_path = os.path.join(self.test_data_dir, "no_amount.csv")


        # Create a sample CSV file
        with open(self.sample_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])
            writer.writerow(["2023-01-01","Initial Balance","","",100.00]) # Processed, amount 0, type ""
            writer.writerow(["2023-01-02","Coffee Shop","10.50","",89.50]) # Processed
            writer.writerow(["2023-01-03","Paycheck","","1500.00",1589.50]) # Processed
            writer.writerow(["2023-01-04","InvalidData","ABC","",1589.50]) # Skipped due to InvalidOperation
            writer.writerow(["","Missing Date Entry","10","",1579.50]) # Skipped due to missing date
            writer.writerow(["2023-01-05","Zero Debit","0","",1579.50]) # Processed, amount 0, type ""
            writer.writerow(["2023-01-06","Zero Credit","","0",1579.50]) # Processed, amount 0, type ""


        # Create an empty CSV file (only headers)
        with open(self.empty_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])

        # Create a malformed CSV (e.g. numbers cannot be parsed)
        with open(self.malformed_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])
            writer.writerow(["2023-01-01","Bad Number","not-a-number","",100.00]) # Skipped

        # Create a CSV with missing headers
        with open(self.missing_headers_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Description","Amount Debit"]) # Missing Credit and Balance
            writer.writerow(["2023-01-01","Test","10.00"])

        # Create a CSV with a row that has no amount (and is not 'initial balance')
        with open(self.no_amount_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Description","Amount Debit","Amount Credit","Balance"])
            writer.writerow(["2023-01-01","Just Info","","",100.00]) # Skipped


    def tearDown(self):
        for f_name in [self.sample_csv_path, self.empty_csv_path, self.malformed_csv_path, self.missing_headers_csv_path, self.no_amount_csv_path]:
            if os.path.exists(f_name):
                os.remove(f_name)
        if os.path.exists(self.test_data_dir):
            os.rmdir(self.test_data_dir)

    def test_parse_valid_csv(self):
        transactions = parse_statement_csv(self.sample_csv_path)
        # Expected: "Opening Balance", "Coffee Shop", "Paycheck", "Zero Debit", "Zero Credit"
        # Skipped: "InvalidData", "Missing Date Entry"
        self.assertEqual(len(transactions), 5)

        self.assertEqual(transactions[0]["description"], "Initial Balance")
        self.assertEqual(transactions[0]["amount"], Decimal("0.00"))
        self.assertEqual(transactions[0]["type"], "")
        self.assertEqual(transactions[0]["balance"], Decimal("100.00"))

        self.assertEqual(transactions[1]["description"], "Coffee Shop")
        self.assertEqual(transactions[1]["amount"], Decimal("-10.50"))
        self.assertEqual(transactions[1]["type"], "debit")
        self.assertEqual(transactions[1]["balance"], Decimal("89.50"))

        self.assertEqual(transactions[2]["description"], "Paycheck")
        self.assertEqual(transactions[2]["amount"], Decimal("1500.00"))
        self.assertEqual(transactions[2]["type"], "credit")
        self.assertEqual(transactions[2]["balance"], Decimal("1589.50"))

        self.assertEqual(transactions[3]["description"], "Zero Debit")
        self.assertEqual(transactions[3]["amount"], Decimal("0.00"))
        self.assertEqual(transactions[3]["type"], "") # Type is empty because amount is zero
        self.assertEqual(transactions[3]["balance"], Decimal("1579.50"))

        self.assertEqual(transactions[4]["description"], "Zero Credit")
        self.assertEqual(transactions[4]["amount"], Decimal("0.00"))
        self.assertEqual(transactions[4]["type"], "") # Type is empty because amount is zero
        self.assertEqual(transactions[4]["balance"], Decimal("1579.50"))


    def test_parse_non_existent_file(self):
        transactions = parse_statement_csv("non_existent.csv")
        self.assertEqual(transactions, [])

    def test_parse_empty_csv(self):
        transactions = parse_statement_csv(self.empty_csv_path)
        self.assertEqual(transactions, [])

    def test_parse_malformed_csv_values(self):
        # The malformed row ("Bad Number") should be skipped, returning no transactions from that file
        transactions = parse_statement_csv(self.malformed_csv_path)
        self.assertEqual(len(transactions), 0)

    def test_parse_csv_missing_headers(self):
        transactions = parse_statement_csv(self.missing_headers_csv_path)
        self.assertEqual(transactions, [])

    def test_parse_no_amount_row(self):
        # Row with "Just Info" and no amount fields should be skipped
        transactions = parse_statement_csv(self.no_amount_csv_path)
        self.assertEqual(len(transactions), 0)


if __name__ == '__main__':
    unittest.main()
