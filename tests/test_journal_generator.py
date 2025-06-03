import unittest
from datetime import date
from decimal import Decimal
from src.journal_generator import generate_journal_entries, apply_rules_to_transaction

class TestJournalGenerator(unittest.TestCase):

    def setUp(self):
        self.accounts_config = [
            {"name": "Main Checking", "type": "Asset"},
            {"name": "Office Expenses", "type": "Expense"},
            {"name": "Software", "type": "Expense"},
            {"name": "Consulting Revenue", "type": "Revenue"},
            {"name": "Suspense Account", "type": "Equity"}
        ]
        self.rules_config = [
            {"name": "Office Rule", "conditions": {"keywords": ["staples", "office depot"]}, "account": "Office Expenses"},
            {"name": "Software Rule", "conditions": {"keywords": ["adobe", "microsoft subs"]}, "account": "Software"},
            {"name": "Consulting Income", "conditions": {"keywords": ["client payment", "consulting fee"]}, "account": "Consulting Revenue"}
        ]
        self.default_bank = "Main Checking"
        self.default_suspense = "Suspense Account"

    def test_apply_rules(self):
        rule = apply_rules_to_transaction("Invoice from STAPLES", Decimal("100"), self.rules_config)
        self.assertIsNotNone(rule)
        self.assertEqual(rule["account"], "Office Expenses")

        rule_no_match = apply_rules_to_transaction("Unknown Vendor XYZ", Decimal("50"), self.rules_config)
        self.assertIsNone(rule_no_match)

        rule_case_insensitive = apply_rules_to_transaction("payment for ADOBE products", Decimal("20"), self.rules_config)
        self.assertIsNotNone(rule_case_insensitive)
        self.assertEqual(rule_case_insensitive["account"], "Software")

        rule_empty_desc = apply_rules_to_transaction("", Decimal("20"), self.rules_config)
        self.assertIsNone(rule_empty_desc, "Should not match if description is empty")

        rule_empty_config = apply_rules_to_transaction("Valid description", Decimal("20"), [])
        self.assertIsNone(rule_empty_config, "Should not match if rules config is empty")


    def test_generate_entry_matched_with_rule(self):
        matched_results = [{
            "statement": {"id": "s1", "date": date(2023, 1, 10), "description": "STAPLES STORE 001", "amount": Decimal("-50.00")},
            "voucher": {"id": "v1", "vendor_name": "Staples", "raw_text": "Staples office supplies receipt", "total_amount": Decimal("50.00")},
            "status": "matched"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "auto_generated_rule")
        self.assertEqual(entry["description"], "Staples - STAPLES STORE 001")
        self.assertEqual(entry["postings"][0]["account"], "Office Expenses") # Debit
        self.assertEqual(entry["postings"][0]["debit"], Decimal("50.00"))
        self.assertEqual(entry["postings"][1]["account"], self.default_bank) # Credit
        self.assertEqual(entry["postings"][1]["credit"], Decimal("50.00"))
        self.assertEqual(entry["source_statement_id"], "s1")
        self.assertEqual(entry["source_voucher_id"], "v1")


    def test_generate_entry_matched_no_rule(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 11), "description": "RANDOM CORP PAYMENT", "amount": Decimal("-120.00")},
            "voucher": {"vendor_name": "Random Corp", "raw_text": "Random Corp invoice details", "total_amount": Decimal("120.00")},
            "status": "matched"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "auto_generated_matched_no_rule")
        self.assertEqual(entry["description"], "Random Corp - RANDOM CORP PAYMENT")
        self.assertEqual(entry["postings"][0]["account"], self.default_suspense) # Debit
        self.assertEqual(entry["postings"][0]["debit"], Decimal("120.00"))
        self.assertEqual(entry["postings"][1]["account"], self.default_bank) # Credit

    def test_generate_entry_unmatched_debit(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 12), "description": "MYSTERY DEBIT", "amount": Decimal("-30.00")},
            "voucher": None,
            "status": "unmatched"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "unmatched_debit")
        self.assertEqual(entry["description"], "MYSTERY DEBIT")
        self.assertEqual(entry["postings"][0]["account"], self.default_suspense) # Debit
        self.assertEqual(entry["postings"][0]["debit"], Decimal("30.00"))
        self.assertEqual(entry["postings"][1]["account"], self.default_bank) # Credit

    def test_generate_entry_ignored_credit_with_rule(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 13), "description": "Client Payment from ACME", "amount": Decimal("500.00")},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "auto_generated_rule_income")
        self.assertEqual(entry["postings"][0]["account"], self.default_bank) # Debit Bank
        self.assertEqual(entry["postings"][0]["debit"], Decimal("500.00"))
        self.assertEqual(entry["postings"][1]["account"], "Consulting Revenue") # Credit Revenue

    def test_generate_entry_ignored_credit_no_rule(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 14), "description": "MYSTERY DEPOSIT", "amount": Decimal("250.00")},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "unmatched_credit")
        self.assertEqual(entry["postings"][0]["account"], self.default_bank) # Debit Bank
        self.assertEqual(entry["postings"][1]["account"], self.default_suspense) # Credit Suspense

    def test_no_entry_for_zero_amount_ignored(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 15), "description": "Zero Balance Adjustment", "amount": Decimal("0.00")},
            "voucher": None,
            "status": "ignored_credit_or_zero"
        }]
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries), 0)

    def test_default_bank_not_in_config(self):
        matched_results = [{
            "statement": {"date": date(2023, 1, 12), "description": "MYSTERY DEBIT", "amount": Decimal("-30.00")},
            "voucher": None,
            "status": "unmatched"
        }]
        custom_bank_name = "NonExistent Bank Account"
        entries = generate_journal_entries(matched_results, self.accounts_config, self.rules_config, custom_bank_name, self.default_suspense)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        # Check that the custom bank name string is used directly if not found in config
        self.assertEqual(entry["postings"][1]["account"], custom_bank_name)

    def test_date_handling_in_statement(self):
        # Statement date as string
        matched_results_str_date = [{
            "statement": {"date": "2023-02-01", "description": "Debit A", "amount": Decimal("-10.00")},
            "voucher": None, "status": "unmatched"
        }]
        entries_str = generate_journal_entries(matched_results_str_date, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries_str), 1)
        self.assertEqual(entries_str[0]["date"], "2023-02-01")

        # Invalid date string
        matched_results_invalid_date = [{
            "statement": {"date": "2023/02/01", "description": "Debit B", "amount": Decimal("-20.00")},
            "voucher": None, "status": "unmatched"
        }]
        entries_invalid = generate_journal_entries(matched_results_invalid_date, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries_invalid), 0, "Should skip entry with invalid date format")

        # Missing date
        matched_results_missing_date = [{
            "statement": {"description": "Debit C", "amount": Decimal("-30.00")}, # Date is missing
            "voucher": None, "status": "unmatched"
        }]
        entries_missing = generate_journal_entries(matched_results_missing_date, self.accounts_config, self.rules_config, self.default_bank, self.default_suspense)
        self.assertEqual(len(entries_missing), 0, "Should skip entry with missing date")


if __name__ == '__main__':
    unittest.main()
