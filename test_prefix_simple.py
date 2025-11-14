#!/usr/bin/env python3
"""
Simple test script for table prefix functionality.

This script tests prefix sanitization logic without requiring database dependencies.
"""

import re


def sanitize_prefix(prefix: str) -> str:
    """
    Sanitize and validate table prefix for SQL Server compliance.
    Only allows alphanumeric characters and underscores (strict mode).
    """
    if not prefix:
        return ""

    # Remove all characters except alphanumeric and underscore (strict mode)
    sanitized = re.sub(r'[^\w]', '', prefix)

    # Ensure prefix doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized

    return sanitized


def test_prefix_sanitization():
    """Test prefix sanitization with various inputs."""

    print("Table Prefix Sanitization Test")
    print("=" * 80)
    print()

    test_cases = [
        ("tbl_", "tbl_", "✓ Valid prefix with underscore"),
        ("staging_", "staging_", "✓ Valid prefix word with underscore"),
        ("dim_", "dim_", "✓ Short valid prefix"),
        ("123_", "_123_", "✓ Prefix starting with number (prepend _)"),
        ("tbl-test", "tbltest", "✓ Invalid character - removed"),
        ("tbl@test", "tbltest", "✓ Invalid character @ removed"),
        ("tbl test", "tbltest", "✓ Space removed"),
        ("tbl.test", "tbltest", "✓ Dot removed"),
        ("$tbl_", "tbl_", "✓ Leading $ removed"),
        ("", "", "✓ Empty prefix"),
        ("test_123_", "test_123_", "✓ Valid alphanumeric with underscores"),
    ]

    passed = 0
    failed = 0

    for input_prefix, expected, description in test_cases:
        result = sanitize_prefix(input_prefix)

        if result == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        print(f"[{status}] {description}")
        print(f"      Input:    '{input_prefix}'")
        print(f"      Expected: '{expected}'")
        print(f"      Got:      '{result}'")
        print()

    # Test table name generation examples
    print("=" * 80)
    print("Table Name Generation Examples (with prefix 'tbl_')")
    print("-" * 80)
    print()

    prefix = "tbl_"
    table_names = [
        "CustomerAccount",
        "OrderHistory",
        "SalesData",
        "PartyDetails",
    ]

    for table in table_names:
        prefixed = f"{prefix}{table}"
        print(f"  {table:<25} → {prefixed}")

    print()

    # Summary
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = test_prefix_sanitization()
    sys.exit(0 if success else 1)
