import unittest
from decimal import Decimal
from datetime import date
from src.voucher_processor import structure_voucher_data, ocr_placeholder

class TestVoucherProcessor(unittest.TestCase):

    def test_structure_valid_data(self):
        raw_data = {
            "vendor_name": "Test Vendor Inc.",
            "transaction_date": "2023-11-15",
            "total_amount": "199.99",
            "currency": "CAD",
            "line_items": [
                {"description": "Product 1", "quantity": 2, "unit_price": "50.00", "total_price": "100.00"},
                {"description": "Product 2", "quantity": 1, "unit_price": "99.99", "total_price": "99.99"}
            ],
            "raw_text": "Some raw OCR text here."
        }
        voucher = structure_voucher_data(raw_data)
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher["vendor_name"], "Test Vendor Inc.")
        self.assertEqual(voucher["transaction_date"], date(2023, 11, 15))
        self.assertEqual(voucher["total_amount"], Decimal("199.99"))
        self.assertEqual(voucher["currency"], "CAD")
        self.assertEqual(len(voucher["line_items"]), 2)
        self.assertEqual(voucher["line_items"][0]["description"], "Product 1")
        self.assertEqual(voucher["line_items"][0]["total_price"], Decimal("100.00"))
        self.assertEqual(voucher["raw_text"], "Some raw OCR text here.")

    def test_structure_missing_required_fields(self):
        # Missing transaction_date and total_amount
        raw_data_missing_multiple = {"vendor_name": "Incomplete Data Inc."}
        self.assertIsNone(structure_voucher_data(raw_data_missing_multiple), "Failed on missing date and amount")

        # Missing vendor_name
        raw_data_missing_vendor = {"transaction_date": "2023-11-15", "total_amount": "50.00"}
        self.assertIsNone(structure_voucher_data(raw_data_missing_vendor), "Failed on missing vendor name")

        # Missing total_amount
        raw_data_missing_amount = {"vendor_name": "Vendor", "transaction_date": "2023-11-15"}
        self.assertIsNone(structure_voucher_data(raw_data_missing_amount), "Failed on missing amount")

        # Missing transaction_date
        raw_data_missing_date = {"vendor_name": "Vendor", "total_amount": "50.00"}
        self.assertIsNone(structure_voucher_data(raw_data_missing_date), "Failed on missing date")


    def test_structure_invalid_date_format(self):
        raw_data = {
            "vendor_name": "Bad Date Format",
            "transaction_date": "15/11/2023", # Invalid format
            "total_amount": "100.00"
        }
        self.assertIsNone(structure_voucher_data(raw_data))

    def test_structure_invalid_amount_format(self):
        raw_data = {
            "vendor_name": "Bad Amount Format",
            "transaction_date": "2023-11-15",
            "total_amount": "one hundred dollars" # Invalid format
        }
        self.assertIsNone(structure_voucher_data(raw_data))

    def test_structure_negative_total_amount(self):
        raw_data = {
            "vendor_name": "Negative Amount Store",
            "transaction_date": "2023-11-15",
            "total_amount": "-75.25"
        }
        voucher = structure_voucher_data(raw_data)
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher["total_amount"], Decimal("75.25"))


    def test_structure_default_currency(self):
        raw_data = {
            "vendor_name": "No Currency Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "50.00"
            # Currency field is missing
        }
        voucher = structure_voucher_data(raw_data)
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher["currency"], "USD") # Default currency

    def test_structure_invalid_currency_code(self):
        raw_data_long = {
            "vendor_name": "Invalid Currency Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "50.00",
            "currency": "USDD" # Invalid code (too long)
        }
        voucher_long = structure_voucher_data(raw_data_long)
        self.assertIsNotNone(voucher_long)
        self.assertEqual(voucher_long["currency"], "USD") # Should default

        raw_data_short = {
            "vendor_name": "Invalid Currency Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "50.00",
            "currency": "US" # Invalid code (too short)
        }
        voucher_short = structure_voucher_data(raw_data_short)
        self.assertIsNotNone(voucher_short)
        self.assertEqual(voucher_short["currency"], "USD") # Should default

        raw_data_non_str = {
            "vendor_name": "Invalid Currency Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "50.00",
            "currency": 123 # Invalid type
        }
        voucher_non_str = structure_voucher_data(raw_data_non_str)
        self.assertIsNotNone(voucher_non_str)
        self.assertEqual(voucher_non_str["currency"], "USD") # Should default


    def test_structure_line_items_validation(self):
        # Line item with non-numeric quantity (ValueError for int())
        raw_data_bad_qty = {
            "vendor_name": "Bad Line Item Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "100.00",
            "line_items": [
                {"description": "Good Item", "quantity": 1, "unit_price": "50.00", "total_price": "50.00"},
                {"description": "Bad Item Qty", "quantity": "two", "unit_price": "25.00", "total_price": "50.00"}
            ]
        }
        voucher_bad_qty = structure_voucher_data(raw_data_bad_qty)
        self.assertIsNotNone(voucher_bad_qty)
        self.assertEqual(len(voucher_bad_qty["line_items"]), 1, "Bad quantity item should be skipped")
        self.assertEqual(voucher_bad_qty["line_items"][0]["description"], "Good Item")

        # Line item with non-numeric unit_price (InvalidOperation for Decimal())
        raw_data_bad_price = {
            "vendor_name": "Bad Line Item Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "100.00",
            "line_items": [
                {"description": "Good Item", "quantity": 1, "unit_price": "50.00", "total_price": "50.00"},
                {"description": "Bad Item Price", "quantity": 2, "unit_price": "twenty", "total_price": "40.00"}
            ]
        }
        voucher_bad_price = structure_voucher_data(raw_data_bad_price)
        self.assertIsNotNone(voucher_bad_price)
        self.assertEqual(len(voucher_bad_price["line_items"]), 1, "Bad unit_price item should be skipped")
        self.assertEqual(voucher_bad_price["line_items"][0]["description"], "Good Item")


        # Line item where qty * unit_price != total_price (should log warning but still include)
        raw_data_mismatch = {
            "vendor_name": "Mismatch Price Vendor",
            "transaction_date": "2023-11-15",
            "total_amount": "100.00",
            "line_items": [
                {"description": "Mismatch Item", "quantity": 1, "unit_price": "40.00", "total_price": "45.00"} # 5.00 diff
            ]
        }
        voucher_mismatch = structure_voucher_data(raw_data_mismatch)
        self.assertIsNotNone(voucher_mismatch)
        self.assertEqual(len(voucher_mismatch["line_items"]), 1)
        self.assertEqual(voucher_mismatch["line_items"][0]["total_price"], Decimal("45.00"))

        # Line item with minimal rounding diff (should NOT log warning and include)
        # 2 * 20.01 = 40.02. Total price 40.03. Difference is 0.01.
        # Tolerance: 0.015 * 2 = 0.03. Since 0.01 < 0.03, it should pass.
        raw_data_rounding = {
            "vendor_name": "Rounding Vendor",
            "transaction_date": "2023-11-16",
            "total_amount": "40.03",
            "line_items": [
                {"description": "Rounded Item", "quantity": 2, "unit_price": "20.01", "total_price": "40.03"}
            ]
        }
        voucher_rounding = structure_voucher_data(raw_data_rounding)
        self.assertIsNotNone(voucher_rounding)
        self.assertEqual(len(voucher_rounding["line_items"]), 1)
        self.assertEqual(voucher_rounding["line_items"][0]["total_price"], Decimal("40.03"))


    def test_ocr_placeholder(self):
        # Simple test to ensure placeholder returns a dict with expected keys
        ocr_data = ocr_placeholder("any_path.png")
        self.assertIsInstance(ocr_data, dict)
        self.assertIn("vendor_name", ocr_data)
        self.assertIn("transaction_date", ocr_data)
        self.assertIn("total_amount", ocr_data)

if __name__ == '__main__':
    unittest.main()
