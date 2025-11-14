#!/usr/bin/env python3
"""
Test script to demonstrate filename sanitization.

This script shows how filenames are sanitized without requiring a database connection.
"""

from pathlib import Path
from filename_sanitizer import FilenameSanitizer, create_timestamp_sanitizer

def test_sanitization():
    """Test the sanitization on actual CSV files."""
    print("Filename Sanitization Test")
    print("=" * 80)
    print()

    # Get CSV files from the csv_files directory
    csv_dir = Path("csv_files")
    csv_files = sorted(csv_dir.glob("*.csv"))

    if not csv_files:
        print("No CSV files found in csv_files directory")
        return

    # Create sanitizer
    sanitizer = FilenameSanitizer()

    print(f"Found {len(csv_files)} CSV file(s) to process:\n")

    # Process each file
    results = []
    for csv_file in csv_files:
        filename = csv_file.name
        table_name = sanitizer.sanitize(filename)
        is_valid = sanitizer.validate_table_name(table_name)
        status = "✓" if is_valid else "✗"

        results.append({
            'filename': filename,
            'table_name': table_name,
            'valid': is_valid,
            'status': status
        })

        print(f"{status} {filename:50s} → {table_name}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print("-" * 80)
    total = len(results)
    valid = sum(1 for r in results if r['valid'])
    invalid = total - valid

    print(f"Total files:     {total}")
    print(f"Valid names:     {valid}")
    print(f"Invalid names:   {invalid}")

    if invalid > 0:
        print("\nInvalid table names:")
        for r in results:
            if not r['valid']:
                print(f"  - {r['filename']} → {r['table_name']}")

    print("\n" + "=" * 80)
    print("\nConfiguration:")
    print("-" * 80)
    print(f"PascalCase enabled:  {sanitizer.rules.use_pascal_case}")
    print(f"Max name length:     {sanitizer.rules.max_length}")
    print(f"Pattern rules:       {len(sanitizer.rules.strip_patterns)} patterns")
    print()

    # Show what patterns are being used
    print("Sanitization patterns (first 10):")
    for i, pattern in enumerate(sanitizer.rules.strip_patterns[:10], 1):
        print(f"  {i:2d}. {pattern}")

    if len(sanitizer.rules.strip_patterns) > 10:
        print(f"  ... and {len(sanitizer.rules.strip_patterns) - 10} more patterns")

    print()


if __name__ == "__main__":
    test_sanitization()
