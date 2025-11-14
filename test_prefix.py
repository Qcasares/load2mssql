#!/usr/bin/env python3
"""
Test script for table prefix functionality.

This script tests the table prefix feature without requiring a database connection.
"""

import sys
from pathlib import Path
from load_csv_to_mssql import CSVToMSSQLLoader


def test_prefix_functionality():
    """Test table prefix with various scenarios."""

    print("Table Prefix Functionality Test")
    print("=" * 80)
    print()

    # Create a loader instance with default config
    try:
        loader = CSVToMSSQLLoader("config.yaml")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False

    # Test scenarios
    test_cases = [
        {
            "filename": "CustomerAccount_2025-10-09_183621.csv",
            "description": "Timestamped filename with default prefix"
        },
        {
            "filename": "OrderHistory_20251114_093000.csv",
            "description": "Different timestamp format"
        },
        {
            "filename": "sales_data.csv",
            "description": "Simple filename"
        },
        {
            "filename": "PartyDetails_2025-10-09_183712.csv",
            "description": "Another timestamped file"
        }
    ]

    print("Testing table name generation:")
    print("-" * 80)

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        filename = test["filename"]
        description = test["description"]

        try:
            table_name = loader.get_table_name(filename)
            print(f"{i}. {description}")
            print(f"   Input:  {filename}")
            print(f"   Output: {table_name}")

            # Check if prefix was applied (based on config)
            if loader.table_config.table_prefix:
                sanitized_prefix = loader._sanitize_prefix(loader.table_config.table_prefix)
                if table_name.startswith(sanitized_prefix):
                    print(f"   ✓ Prefix '{sanitized_prefix}' applied correctly")
                else:
                    print(f"   ✗ Expected prefix '{sanitized_prefix}' not found")
                    all_passed = False
            else:
                print(f"   ℹ No prefix configured")

            print()

        except Exception as e:
            print(f"   ✗ Error: {e}")
            all_passed = False
            print()

    # Test prefix validation
    print("=" * 80)
    print("Testing prefix validation:")
    print("-" * 80)

    prefix_tests = [
        ("tbl_", "tbl_", "Valid prefix with underscore"),
        ("staging_", "staging_", "Valid prefix word with underscore"),
        ("123_", "_123_", "Prefix starting with number (should prepend _)"),
        ("tbl-test", "tbltest", "Invalid character - (should be removed)"),
        ("tbl@test", "tbltest", "Invalid character @ (should be removed)"),
        ("", "", "Empty prefix"),
    ]

    for i, (input_prefix, expected, description) in enumerate(prefix_tests, 1):
        result = loader._sanitize_prefix(input_prefix)
        status = "✓" if result == expected else "✗"
        print(f"{i}. {description}")
        print(f"   Input:    '{input_prefix}'")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")
        print(f"   Status:   {status}")
        print()

        if result != expected:
            all_passed = False

    # Summary
    print("=" * 80)
    if all_passed:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


if __name__ == "__main__":
    success = test_prefix_functionality()
    sys.exit(0 if success else 1)
