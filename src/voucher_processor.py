from decimal import Decimal, InvalidOperation
from datetime import datetime

def ocr_placeholder(image_path_or_binary):
    """
    Placeholder function for OCR processing.
    In a real implementation, this function would take an image path or binary data,
    perform OCR, and return structured text or a dictionary.
    For now, it returns a predefined dictionary simulating OCR output.
    """
    print(f"OCR Placeholder: Simulating OCR for '{image_path_or_binary}'")
    # Simulate extracted data for a sample receipt
    return {
        "vendor_name": "Example Store",
        "transaction_date": "2023-10-20",
        "total_amount": "125.50",
        "currency": "USD",
        "line_items": [
            {"description": "Item A", "quantity": 2, "unit_price": "50.00", "total_price": "100.00"},
            {"description": "Item B", "quantity": 1, "unit_price": "25.50", "total_price": "25.50"}
        ],
        "raw_text": "Example Store\n123 Main St\nDate: 2023-10-20\nItem A 2 @ 50.00 = 100.00\nItem B 1 @ 25.50 = 25.50\nTotal: 125.50"
    }

def structure_voucher_data(extracted_data):
    """
    Structures the data extracted from a voucher (e.g., by OCR).
    Validates and normalizes data types.

    Args:
        extracted_data (dict): A dictionary containing data fields like
                               vendor_name, transaction_date, total_amount, etc.
                               Amounts should be strings that can be converted to Decimal.
                               Dates should be strings in 'YYYY-MM-DD' format.

    Returns:
        dict: A structured voucher dictionary with validated and typed data,
              or None if essential data is missing or invalid.
    """
    if not isinstance(extracted_data, dict):
        print("Error: Extracted data must be a dictionary.")
        return None

    structured_voucher = {}

    # Vendor Name (string, required)
    vendor_name = extracted_data.get("vendor_name")
    if not vendor_name or not isinstance(vendor_name, str):
        print("Error: Missing or invalid vendor_name.")
        return None
    structured_voucher["vendor_name"] = vendor_name.strip()

    # Transaction Date (date object, required)
    date_str = extracted_data.get("transaction_date")
    if not date_str or not isinstance(date_str, str):
        print("Error: Missing or invalid transaction_date string.")
        return None
    try:
        structured_voucher["transaction_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format for transaction_date: {date_str}. Expected YYYY-MM-DD.")
        return None

    # Total Amount (Decimal, required)
    total_amount_str = extracted_data.get("total_amount")
    if not total_amount_str: # Can be string or number, try to convert
        print("Error: Missing total_amount.")
        return None
    try:
        structured_voucher["total_amount"] = Decimal(str(total_amount_str))
    except InvalidOperation:
        print(f"Error: Invalid format for total_amount: {total_amount_str}.")
        return None

    if structured_voucher["total_amount"] < Decimal(0):
        print(f"Warning: total_amount is negative: {structured_voucher['total_amount']}. Making it positive.")
        structured_voucher["total_amount"] = abs(structured_voucher['total_amount'])


    # Currency (string, optional, default to 'USD' if not provided)
    currency = extracted_data.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3:
        print(f"Warning: Invalid currency code: {currency}. Defaulting to USD.")
        structured_voucher["currency"] = "USD"
    else:
        structured_voucher["currency"] = currency.upper()

    # Line Items (list of dicts, optional)
    # Basic validation for line items if they exist
    line_items_data = extracted_data.get("line_items")
    structured_line_items = []
    if isinstance(line_items_data, list):
        for item_data in line_items_data:
            if isinstance(item_data, dict):
                try:
                    item = {
                        "description": str(item_data.get("description","")).strip(),
                        "quantity": int(item_data.get("quantity", 1)),
                        "unit_price": Decimal(str(item_data.get("unit_price", "0"))),
                        "total_price": Decimal(str(item_data.get("total_price", "0")))
                    }
                    # Basic check: quantity * unit_price should be somewhat close to total_price
                    # This is a loose check due to potential rounding in source data
                    if item["quantity"] > 0 and item["unit_price"] > 0 and item["total_price"] > 0:
                        calculated_total = Decimal(item["quantity"]) * item["unit_price"]
                        # Allow small diff per quantity, using a small epsilon for comparison
                        # Check if the absolute difference is greater than a small tolerance (e.g., 0.01 per item quantity)
                        if not (abs(calculated_total - item["total_price"]) < (Decimal('0.015') * item["quantity"])): # Adjusted tolerance
                            print(f"Warning: Line item total price {item['total_price']} does not match quantity {item['quantity']} * unit_price {item['unit_price']} = {calculated_total} for '{item['description']}'. Using provided total_price.")
                    structured_line_items.append(item)
                except (InvalidOperation, ValueError) as e:
                    print(f"Warning: Skipping malformed line item {item_data}: {e}")
    structured_voucher["line_items"] = structured_line_items

    # Raw Text (string, optional)
    raw_text = extracted_data.get("raw_text")
    structured_voucher["raw_text"] = str(raw_text).strip() if raw_text else ""

    return structured_voucher

if __name__ == '__main__':
    print("--- Simulating OCR and Structuring ---")
    simulated_ocr_output = ocr_placeholder("dummy_receipt.jpg")
    print(f"Simulated OCR Output: {simulated_ocr_output}")

    structured_data = structure_voucher_data(simulated_ocr_output)
    if structured_data:
        print("\nStructured Voucher Data (Success):")
        for key, value in structured_data.items():
            if isinstance(value, list) and value: # Pretty print line items
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value} (Type: {type(value).__name__})")
    else:
        print("\nStructuring failed.")

    print("\n--- Test Case: Missing Required Fields ---")
    missing_fields_data = {"vendor_name": "Test Vendor"} # Missing date, amount
    structured_missing = structure_voucher_data(missing_fields_data)
    if not structured_missing:
        print("Correctly handled missing required fields.")

    print("\n--- Test Case: Invalid Data Types ---")
    invalid_types_data = {
        "vendor_name": "Valid Vendor",
        "transaction_date": "2023/10/25", # Invalid date format
        "total_amount": "100.00"
    }
    structured_invalid_type = structure_voucher_data(invalid_types_data)
    if not structured_invalid_type:
        print("Correctly handled invalid date format.")

    invalid_amount_data = {
        "vendor_name": "Valid Vendor",
        "transaction_date": "2023-10-25",
        "total_amount": "one hundred" # Invalid amount format
    }
    structured_invalid_amount = structure_voucher_data(invalid_amount_data)
    if not structured_invalid_amount:
        print("Correctly handled invalid amount format.")

    print("\n--- Test Case: Negative Total Amount ---")
    negative_total_data = {
        "vendor_name": "Refund Place",
        "transaction_date": "2023-10-26",
        "total_amount": "-50.00", # Negative, should be converted to positive
        "currency": "USD"
    }
    structured_negative_total = structure_voucher_data(negative_total_data)
    if structured_negative_total and structured_negative_total["total_amount"] == Decimal("50.00"):
        print(f"Correctly handled negative total_amount: {structured_negative_total['total_amount']}")

    print("\n--- Test Case: Line Item Mismatch ---")
    line_item_mismatch_data = {
        "vendor_name": "Mismatch Store",
        "transaction_date": "2023-10-27",
        "total_amount": "150.00",
        "line_items": [
            {"description": "Item X", "quantity": 1, "unit_price": "50.00", "total_price": "55.00"} # Mismatch
        ]
    }
    structured_mismatch = structure_voucher_data(line_item_mismatch_data)
    if structured_mismatch and structured_mismatch["line_items"]:
        print(f"Handled line item mismatch (check logs for warning): {structured_mismatch['line_items'][0]}")
