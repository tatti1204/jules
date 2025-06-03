import unittest
from datetime import date, timedelta
from decimal import Decimal
from src.matching_engine import find_matching_voucher, match_transactions_to_vouchers

class TestMatchingEngine(unittest.TestCase):

    def setUp(self):
        self.sample_vouchers_orig = [
            {'vendor_name': 'Office Depot', 'transaction_date': date(2023, 10, 4), 'total_amount': Decimal('50.00')},
            {'vendor_name': 'Zoom Video US', 'transaction_date': date(2023, 10, 9), 'total_amount': Decimal('15.00')},
            {'vendor_name': 'Staples Inc.', 'transaction_date': date(2023, 10, 16), 'total_amount': Decimal('75.50')},
            {'vendor_name': 'Generic Restaurant', 'transaction_date': date(2023, 10, 20), 'total_amount': Decimal('25.00')},
            {'vendor_name': 'Shell Gas', 'transaction_date': date(2023, 10, 20), 'total_amount': Decimal('25.00')}, # Same date/amount as Generic Restaurant
            {'vendor_name': 'Simple Mart', 'transaction_date': date(2023, 11, 1), 'total_amount': Decimal('10.00')}
        ]
        # Use a fresh copy for each test to avoid side effects from '_matched' flag
        self.vouchers = [dict(v) for v in self.sample_vouchers_orig]


    def test_find_exact_match_with_keyword(self):
        statement_tx = {'date': date(2023, 10, 5), 'description': 'Payment to Office Depot Store #123', 'amount': Decimal('-50.00')}
        match = find_matching_voucher(statement_tx, self.vouchers, date_tolerance_days=3)
        self.assertIsNotNone(match)
        self.assertEqual(match['vendor_name'], 'Office Depot')

    def test_find_match_date_tolerance(self):
        # Voucher date for Zoom is 2023-10-09
        # Statement date 2023-10-08 makes a 1-day difference
        statement_tx = {'date': date(2023, 10, 8), 'description': 'Zoom Video Conferencing', 'amount': Decimal('-15.00')}

        # Test within tolerance (1 day diff <= 2 days tolerance)
        match_within_tolerance = find_matching_voucher(statement_tx, self.vouchers, date_tolerance_days=2)
        self.assertIsNotNone(match_within_tolerance)
        self.assertEqual(match_within_tolerance['vendor_name'], 'Zoom Video US')

        # Test outside tolerance (1 day diff > 0 days tolerance)
        # For find_matching_voucher, it does not set _matched, match_transactions_to_vouchers does. So self.vouchers is fine.
        match_outside_tolerance = find_matching_voucher(statement_tx, self.vouchers, date_tolerance_days=0)
        self.assertIsNone(match_outside_tolerance)


    def test_no_match_amount_mismatch(self):
        statement_tx = {'date': date(2023, 10, 5), 'description': 'Office Depot', 'amount': Decimal('-50.01')}
        match = find_matching_voucher(statement_tx, self.vouchers)
        self.assertIsNone(match)

    def test_no_match_date_mismatch_strict_tolerance(self):
        statement_tx = {'date': date(2023, 10, 1), 'description': 'Office Depot', 'amount': Decimal('-50.00')} # Date too far for tolerance 2
        match = find_matching_voucher(statement_tx, self.vouchers, date_tolerance_days=2)
        self.assertIsNone(match)

    def test_statement_credit_ignored_by_find_matching_voucher(self):
        statement_tx = {'date': date(2023, 10, 5), 'description': 'Refund from Office Depot', 'amount': Decimal('50.00')}
        match = find_matching_voucher(statement_tx, self.vouchers)
        self.assertIsNone(match)

    def test_voucher_already_marked_as_matched_in_list(self):
        statement_tx1 = {'date': date(2023, 10, 5), 'description': 'Office Depot #1', 'amount': Decimal('-50.00')}
        statement_tx2 = {'date': date(2023, 10, 6), 'description': 'Office Depot #2', 'amount': Decimal('-50.00')}

        # Mark the 'Office Depot' voucher as already matched
        for v in self.vouchers:
            if v['vendor_name'] == 'Office Depot':
                v['_matched'] = True
                break

        match_for_tx2 = find_matching_voucher(statement_tx2, self.vouchers)
        self.assertIsNone(match_for_tx2, "Should not match an already matched voucher")

    def test_match_transactions_to_vouchers_full_run(self):
        statements = [
            {'date': date(2023, 10, 5), 'description': 'OFFICE DEPOT #123', 'amount': Decimal('-50.00')},      # Match 1 (Office Depot)
            {'date': date(2023, 10, 10), 'description': 'ZOOM VIDEO US', 'amount': Decimal('-15.00')},         # Match 2 (Zoom)
            {'date': date(2023, 10, 15), 'description': 'Payment STAPLES INC.', 'amount': Decimal('-75.50')},  # Match 3 (Staples)
            {'date': date(2023, 10, 17), 'description': 'UNRELATED PAYMENT', 'amount': Decimal('-100.00')},   # Unmatched
            {'date': date(2023, 10, 8), 'description': 'CUSTOMER REFUND', 'amount': Decimal('200.00')}      # Ignored (Credit)
        ]

        results = match_transactions_to_vouchers(statements, self.vouchers, date_tolerance_days=3)

        matched_count = sum(1 for res in results if res['status'] == 'matched')
        unmatched_count = sum(1 for res in results if res['status'] == 'unmatched')
        ignored_count = sum(1 for res in results if res['status'] == 'ignored_credit_or_zero')

        self.assertEqual(matched_count, 3, "Incorrect number of matched transactions")
        self.assertEqual(unmatched_count, 1, "Incorrect number of unmatched transactions")
        self.assertEqual(ignored_count, 1, "Incorrect number of ignored transactions")

        # Check that the correct vouchers were marked
        self.assertTrue(self.vouchers[0]['_matched']) # Office Depot
        self.assertTrue(self.vouchers[1]['_matched']) # Zoom
        self.assertTrue(self.vouchers[2]['_matched']) # Staples
        self.assertFalse(self.vouchers[3]['_matched']) # Generic Restaurant (not in statements)
        self.assertFalse(self.vouchers[4]['_matched']) # Shell Gas (not in statements)


    def test_scoring_prefers_closer_date_and_keyword(self):
        statement_tx = {'date': date(2023, 10, 20), 'description': 'Dinner at Generic Restaurant with friends', 'amount': Decimal('-25.00')}
        # self.vouchers[3] is 'Generic Restaurant', date(2023, 10, 20) -> date_diff 0, keyword match (50) + date_score (1*10) = 60
        # self.vouchers[4] is 'Shell Gas', date(2023, 10, 20) -> date_diff 0, no keyword match, date_score (1*10) = 10

        match = find_matching_voucher(statement_tx, self.vouchers, date_tolerance_days=1)
        self.assertIsNotNone(match)
        self.assertEqual(match['vendor_name'], 'Generic Restaurant')

        # Test without direct keyword, but partial keyword for Generic Restaurant
        statement_tx_partial_keyword = {'date': date(2023, 10, 20), 'description': 'Expensive meal at restaurant', 'amount': Decimal('-25.00')}
        # For Generic Restaurant: "restaurant" is a part. Score = (1*10 for date) + (1*10 for "restaurant") = 20
        # For Shell Gas: "shell" or "gas" not in description. Score = (1*10 for date) = 10
        self.vouchers = [dict(v) for v in self.sample_vouchers_orig] # Reset vouchers for clean test
        match_partial = find_matching_voucher(statement_tx_partial_keyword, self.vouchers, date_tolerance_days=1)
        self.assertIsNotNone(match_partial)
        self.assertEqual(match_partial['vendor_name'], 'Generic Restaurant')


    def test_no_vouchers_available_returns_all_debits_unmatched(self):
        statements = [
            {'date': date(2023, 10, 5), 'description': 'Payment A', 'amount': Decimal('-50.00')},
            {'date': date(2023, 10, 6), 'description': 'Payment B', 'amount': Decimal('-60.00')},
            {'date': date(2023, 10, 7), 'description': 'Credit C', 'amount': Decimal('70.00')}
        ]
        results = match_transactions_to_vouchers(statements, [], date_tolerance_days=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(sum(1 for r in results if r['status'] == 'unmatched'), 2)
        self.assertEqual(sum(1 for r in results if r['status'] == 'ignored_credit_or_zero'), 1)

    def test_no_statement_transactions_returns_empty_list(self):
        results = match_transactions_to_vouchers([], self.vouchers, date_tolerance_days=3)
        self.assertEqual(len(results), 0)

    def test_date_conversion_in_find_matching_voucher(self):
        statement_tx_str_date = {'date': "2023-10-05", 'description': 'Office Depot #123', 'amount': Decimal('-50.00')}
        match = find_matching_voucher(statement_tx_str_date, self.vouchers)
        self.assertIsNotNone(match)
        self.assertEqual(match['vendor_name'], 'Office Depot')

        # Test with invalid date string format
        statement_tx_invalid_date = {'date': "2023/10/05", 'description': 'Office Depot', 'amount': Decimal('-50.00')}
        match_invalid = find_matching_voucher(statement_tx_invalid_date, self.vouchers)
        self.assertIsNone(match_invalid, "Should return None for invalid date format in statement")

        # Test with missing date in statement
        statement_tx_no_date = {'description': 'Office Depot', 'amount': Decimal('-50.00')}
        match_no_date = find_matching_voucher(statement_tx_no_date, self.vouchers)
        self.assertIsNone(match_no_date, "Should return None if date is missing in statement")

    def test_voucher_used_only_once_in_match_transactions_to_vouchers(self):
        statements = [
            {'date': date(2023, 11, 1), 'description': 'SIMPLE MART TXN 1', 'amount': Decimal('-10.00')},
            {'date': date(2023, 11, 1), 'description': 'SIMPLE MART TXN 2', 'amount': Decimal('-10.00')}
        ]
        # self.vouchers[-1] is 'Simple Mart', date(2023,11,1), amount 10.00

        results = match_transactions_to_vouchers(statements, self.vouchers)
        self.assertEqual(len(results), 2)

        matched_results = [r for r in results if r['status'] == 'matched']
        self.assertEqual(len(matched_results), 1, "Only one transaction should be matched to the single voucher")

        # Verify the specific voucher was marked
        simple_mart_voucher = next(v for v in self.vouchers if v['vendor_name'] == 'Simple Mart')
        self.assertTrue(simple_mart_voucher['_matched'])

if __name__ == '__main__':
    unittest.main()
