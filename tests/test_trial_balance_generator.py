import unittest
import os
import csv
from decimal import Decimal
from src.trial_balance_generator import generate_trial_balance
from collections import defaultdict

class TestTrialBalanceGenerator(unittest.TestCase):

    def setUp(self):
        self.test_output_dir = "tests/temp_data"
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.output_csv_path = os.path.join(self.test_output_dir, "test_trial_balance.csv")

        self.sample_journal_entries = [
            {
                "date": "2023-01-01", "description": "Entry 1",
                "postings": [
                    {"account": "Cash", "debit": Decimal("1000.00"), "credit": Decimal("0")},
                    {"account": "Capital", "debit": Decimal("0"), "credit": Decimal("1000.00")}
                ]
            },
            {
                "date": "2023-01-02", "description": "Entry 2",
                "postings": [
                    {"account": "Office Supplies", "debit": Decimal("50.00"), "credit": Decimal("0")},
                    {"account": "Cash", "debit": Decimal("0"), "credit": Decimal("50.00")}
                ]
            },
            {
                "date": "2023-01-03", "description": "Entry 3",
                "postings": [
                    {"account": "Cash", "debit": Decimal("200.00"), "credit": Decimal("0")},
                    {"account": "Sales Revenue", "debit": Decimal("0"), "credit": Decimal("200.00")}
                ]
            },
            {
                "date": "2023-01-04", "description": "Entry 4 with string amounts",
                "postings": [
                    {"account": "Rent Expense", "debit": "150.00", "credit": "0.00"},
                    {"account": "Cash", "debit": "0.00", "credit": "150.00"}
                ]
            }
        ]

    def tearDown(self):
        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)

        # Clean up files created by __main__ in the module, if they exist
        main_generated_files = [
            "data/sample_trial_balance.csv",
            "data/empty_trial_balance.csv",
            "data/trial_balance_with_empty_posting.csv",
            "data/trial_balance_invalid_postings.csv" # Added in recent modification
        ]
        for f_name in main_generated_files:
            if os.path.exists(f_name):
                os.remove(f_name)

        # Attempt to remove directories if they are empty
        if os.path.exists(self.test_output_dir) and not os.listdir(self.test_output_dir):
            try:
                os.rmdir(self.test_output_dir)
            except OSError:
                pass
        if os.path.exists("data") and not os.listdir("data"):
            try:
                os.rmdir("data")
            except OSError:
                pass


    def test_generate_trial_balance_success(self):
        success, totals = generate_trial_balance(self.sample_journal_entries, self.output_csv_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_csv_path))

        expected_totals = {
            "Cash": {"debit": Decimal("1200.00"), "credit": Decimal("200.00")},
            "Capital": {"debit": Decimal("0"), "credit": Decimal("1000.00")},
            "Office Supplies": {"debit": Decimal("50.00"), "credit": Decimal("0")},
            "Sales Revenue": {"debit": Decimal("0"), "credit": Decimal("200.00")},
            "Rent Expense": {"debit": Decimal("150.00"), "credit": Decimal("0")}
        }
        self.assertEqual(totals, expected_totals)

        with open(self.output_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            self.assertEqual(header, ["Account Name", "Total Debit", "Total Credit"])

            csv_data = {}
            grand_total_row = None
            for row in reader:
                if row[0] == "GRAND TOTAL":
                    grand_total_row = row
                    continue
                csv_data[row[0]] = {"debit": Decimal(row[1]), "credit": Decimal(row[2])}

            self.assertEqual(csv_data["Cash"]["debit"], Decimal("1200.00"))
            self.assertEqual(csv_data["Cash"]["credit"], Decimal("200.00"))
            self.assertEqual(csv_data["Capital"]["credit"], Decimal("1000.00"))

            self.assertIsNotNone(grand_total_row, "GRAND TOTAL row missing")
            self.assertEqual(grand_total_row[0], "GRAND TOTAL")
            self.assertEqual(Decimal(grand_total_row[1]), Decimal("1400.00"))
            self.assertEqual(Decimal(grand_total_row[2]), Decimal("1400.00"))


    def test_empty_journal_entries(self):
        success, totals = generate_trial_balance([], self.output_csv_path)
        self.assertTrue(success)
        self.assertEqual(totals, {})
        self.assertTrue(os.path.exists(self.output_csv_path))
        with open(self.output_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            self.assertEqual(header, ["Account Name", "Total Debit", "Total Credit"])
            grand_total_row = next(reader, None)
            self.assertIsNotNone(grand_total_row, "GRAND TOTAL row missing for empty entries")
            self.assertEqual(grand_total_row, ["GRAND TOTAL", "0", "0"])
            self.assertEqual(len(list(reader)), 0) # No more rows

    def test_journal_entry_no_postings(self):
        entries = [{"date": "2023-02-01", "description": "Entry with no postings", "postings": []}]
        success, totals = generate_trial_balance(entries, self.output_csv_path)
        self.assertTrue(success)
        self.assertEqual(totals, {})
        with open(self.output_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            self.assertEqual(header, ["Account Name", "Total Debit", "Total Credit"])
            grand_total_row = next(reader, None)
            self.assertIsNotNone(grand_total_row, "GRAND TOTAL row missing for entry with no postings")
            self.assertEqual(grand_total_row, ["GRAND TOTAL", "0", "0"])
            self.assertEqual(len(list(reader)), 0)


    def test_unbalanced_journal_entry_warning_and_processing(self):
        unbalanced_entry = [
            {
                "date": "2023-01-01", "description": "Unbalanced Entry",
                "postings": [
                    {"account": "Cash", "debit": Decimal("100.00"), "credit": Decimal("0")},
                    {"account": "Mystery Revenue", "debit": Decimal("0"), "credit": Decimal("90.00")}
                ]
            }
        ]
        success, totals = generate_trial_balance(unbalanced_entry, self.output_csv_path)
        self.assertTrue(success)
        self.assertEqual(totals["Cash"]["debit"], Decimal("100.00"))
        self.assertEqual(totals["Mystery Revenue"]["credit"], Decimal("90.00"))

        with open(self.output_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            all_rows = list(csv.reader(csvfile))
            last_row = all_rows[-1] # GRAND TOTAL row
            self.assertEqual(last_row[0], "GRAND TOTAL")
            self.assertEqual(Decimal(last_row[1]), Decimal("100.00")) # Total debits
            self.assertEqual(Decimal(last_row[2]), Decimal("90.00")) # Total credits (unbalanced)

    def test_posting_missing_account_name(self):
        entry_with_missing_account = [
            {
                "date": "2023-03-01", "description": "Valid Entry",
                "postings": [
                    {"account": "Valid Account", "debit": Decimal("20"), "credit": Decimal("0")},
                    {"debit": Decimal("10"), "credit": Decimal("0")}, # Missing "account"
                    {"account": "Valid Account", "debit": Decimal("0"), "credit": Decimal("20")}
                 ]
            }
        ]
        success, totals = generate_trial_balance(entry_with_missing_account, self.output_csv_path)
        self.assertTrue(success)
        self.assertIn("Valid Account", totals)
        self.assertEqual(totals["Valid Account"]["debit"], Decimal("20"))
        self.assertEqual(totals["Valid Account"]["credit"], Decimal("20"))
        self.assertEqual(len(totals), 1) # Only 'Valid Account' should be processed

    def test_invalid_amount_in_posting(self):
        entry_with_invalid_amount = [
            {
                "date": "2023-03-01", "description": "Test Invalid Amounts",
                "postings": [
                    {"account": "TestAcc1", "debit": "not-a-decimal", "credit": Decimal("0")},
                    {"account": "TestAcc2", "debit": Decimal("10"), "credit": "bad-credit"},
                    {"account": "TestAcc1", "debit": Decimal("5"), "credit": Decimal("0")} # Valid posting for TestAcc1
                ]
            }
        ]
        success, totals = generate_trial_balance(entry_with_invalid_amount, self.output_csv_path)
        self.assertTrue(success)
        self.assertEqual(totals["TestAcc1"]["debit"], Decimal("5")) # "not-a-decimal" became 0, so only 5 is added
        self.assertEqual(totals["TestAcc1"]["credit"], Decimal("0"))
        self.assertEqual(totals["TestAcc2"]["debit"], Decimal("10"))
        self.assertEqual(totals["TestAcc2"]["credit"], Decimal("0")) # "bad-credit" became 0

if __name__ == '__main__':
    unittest.main()
