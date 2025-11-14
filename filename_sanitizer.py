#!/usr/bin/env python3
"""
Filename Sanitizer Module
=========================

A modular and reusable module for sanitizing CSV filenames to extract clean
SQL Server table names. Handles various real-world naming patterns including
timestamps, dates, and special characters.

Features:
    - Remove timestamps and dates from filenames
    - Strip special characters and normalize table names
    - Support for multiple timestamp/date formats
    - Configurable patterns and rules
    - SQL Server naming compliance

Author: Claude
License: MIT
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field


@dataclass
class SanitizationRules:
    """Configuration for filename sanitization rules."""

    # Patterns to remove from filenames (applied in order)
    strip_patterns: List[str] = field(default_factory=lambda: [
        # Timestamp patterns: _YYYY-MM-DD_HHMMSS, _YYYYMMDD_HHMMSS
        r'_\d{4}-\d{2}-\d{2}_\d{6}',
        r'_\d{8}_\d{6}',

        # Date patterns: _YYYY-MM-DD, _YYYYMMDD, _MMDDYYYY
        r'_\d{4}-\d{2}-\d{2}',
        r'_\d{8}',
        r'_\d{2}\d{2}\d{4}',

        # Time patterns: _HHMMSS, _HH-MM-SS
        r'_\d{6}$',
        r'_\d{2}-\d{2}-\d{2}$',

        # Version patterns: _v1, _v2.0, _ver1
        r'_v\d+(\.\d+)?',
        r'_ver\d+',
        r'_version\d+',

        # Common suffixes: _final, _backup, _temp
        r'_final$',
        r'_backup$',
        r'_temp$',
        r'_copy$',
        r'_old$',
        r'_new$',

        # Sequential numbers: _001, _1, _01
        r'_\d+$',
    ])

    # Characters to replace with underscores
    replace_with_underscore: str = r'[\s\-.]+'

    # Characters to remove entirely
    remove_chars: str = r'[^\w\s]'

    # Maximum table name length (SQL Server limit is 128)
    max_length: int = 128

    # Whether to convert to PascalCase
    use_pascal_case: bool = True

    # Whether to remove consecutive underscores
    remove_consecutive_underscores: bool = True

    # Custom replacement rules (applied before pattern stripping)
    # Format: {pattern: replacement}
    custom_replacements: Dict[str, str] = field(default_factory=dict)


class FilenameSanitizer:
    """
    Sanitizes CSV filenames to produce clean SQL Server table names.

    This class applies a series of configurable rules to transform
    filenames into valid and clean SQL Server table names.

    Example:
        >>> sanitizer = FilenameSanitizer()
        >>> sanitizer.sanitize("CustomerAccount_2025-10-09_183621.csv")
        'CustomerAccount'
        >>> sanitizer.sanitize("sales data-2024.csv")
        'SalesData'
    """

    def __init__(self, rules: Optional[SanitizationRules] = None):
        """
        Initialize the sanitizer with optional custom rules.

        Args:
            rules: Custom sanitization rules. If None, uses default rules.
        """
        self.rules = rules or SanitizationRules()
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.rules.strip_patterns
        ]

    def sanitize(self, filename: str) -> str:
        """
        Sanitize a filename to produce a clean table name.

        Args:
            filename: The CSV filename to sanitize (with or without .csv extension)

        Returns:
            Clean table name suitable for SQL Server

        Example:
            >>> sanitizer.sanitize("CustomerAccount_2025-10-09_183621.csv")
            'CustomerAccount'
        """
        # Remove file extension
        name = Path(filename).stem

        # Apply custom replacements first
        for pattern, replacement in self.rules.custom_replacements.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        # Strip timestamp/date patterns
        name = self._strip_patterns(name)

        # Replace certain characters with underscores
        if self.rules.replace_with_underscore:
            name = re.sub(self.rules.replace_with_underscore, '_', name)

        # Remove unwanted characters
        if self.rules.remove_chars:
            name = re.sub(self.rules.remove_chars, '', name)

        # Remove consecutive underscores
        if self.rules.remove_consecutive_underscores:
            name = re.sub(r'_+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Apply PascalCase if configured
        if self.rules.use_pascal_case:
            name = self._to_pascal_case(name)

        # Ensure it starts with a letter or underscore (SQL Server requirement)
        if name and not name[0].isalpha() and name[0] != '_':
            name = '_' + name

        # Truncate to maximum length
        if len(name) > self.rules.max_length:
            name = name[:self.rules.max_length]

        # Fallback if name is empty
        if not name:
            name = 'UnnamedTable'

        return name

    def _strip_patterns(self, name: str) -> str:
        """
        Remove timestamp and date patterns from the name.

        Args:
            name: The name to process

        Returns:
            Name with patterns removed
        """
        for pattern in self._compiled_patterns:
            name = pattern.sub('', name)
        return name

    def _to_pascal_case(self, name: str) -> str:
        """
        Convert name to PascalCase.

        Args:
            name: The name to convert

        Returns:
            PascalCase version of the name

        Example:
            >>> self._to_pascal_case("customer_account")
            'CustomerAccount'
            >>> self._to_pascal_case("CustomerAccount")
            'CustomerAccount'
        """
        # If there are underscores, split and capitalize each part
        if '_' in name:
            parts = name.split('_')
            pascal = ''.join(word.capitalize() for word in parts if word)
            return pascal

        # If already in PascalCase or single word, preserve it if it starts with uppercase
        # Otherwise capitalize it
        if name and name[0].isupper():
            return name
        else:
            return name.capitalize() if name else name

    def sanitize_batch(self, filenames: List[str]) -> Dict[str, str]:
        """
        Sanitize multiple filenames at once.

        Args:
            filenames: List of filenames to sanitize

        Returns:
            Dictionary mapping original filenames to sanitized table names

        Example:
            >>> sanitizer.sanitize_batch([
            ...     "CustomerAccount_2025-10-09_183621.csv",
            ...     "sales_data.csv"
            ... ])
            {
                'CustomerAccount_2025-10-09_183621.csv': 'CustomerAccount',
                'sales_data.csv': 'SalesData'
            }
        """
        return {filename: self.sanitize(filename) for filename in filenames}

    def validate_table_name(self, table_name: str) -> bool:
        """
        Validate that a table name is valid for SQL Server.

        Args:
            table_name: The table name to validate

        Returns:
            True if valid, False otherwise
        """
        # SQL Server table name rules:
        # - Must start with letter, @, #, or _
        # - Can contain letters, digits, @, $, #, _
        # - Max 128 characters
        # - Cannot be a reserved keyword (simplified check)

        if not table_name or len(table_name) > 128:
            return False

        if not (table_name[0].isalpha() or table_name[0] in '@#_'):
            return False

        # Check valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@$#')
        if not all(c in valid_chars for c in table_name):
            return False

        return True

    def add_custom_pattern(self, pattern: str) -> None:
        """
        Add a custom pattern to strip from filenames.

        Args:
            pattern: Regular expression pattern to add

        Example:
            >>> sanitizer.add_custom_pattern(r'_export$')
        """
        self.rules.strip_patterns.append(pattern)
        self._compiled_patterns.append(re.compile(pattern, re.IGNORECASE))

    def add_custom_replacement(self, pattern: str, replacement: str) -> None:
        """
        Add a custom replacement rule.

        Args:
            pattern: Regular expression pattern to match
            replacement: String to replace matches with

        Example:
            >>> sanitizer.add_custom_replacement(r'cust', 'Customer')
        """
        self.rules.custom_replacements[pattern] = replacement


# Pre-configured sanitizers for common use cases

def create_timestamp_sanitizer() -> FilenameSanitizer:
    """
    Create a sanitizer optimized for timestamped filenames.

    Returns:
        FilenameSanitizer configured for timestamp removal

    Example:
        >>> sanitizer = create_timestamp_sanitizer()
        >>> sanitizer.sanitize("Orders_2025-10-09_183621.csv")
        'Orders'
    """
    return FilenameSanitizer()


def create_simple_sanitizer() -> FilenameSanitizer:
    """
    Create a simple sanitizer that only removes extensions and normalizes.

    Returns:
        FilenameSanitizer with minimal processing

    Example:
        >>> sanitizer = create_simple_sanitizer()
        >>> sanitizer.sanitize("my-data.csv")
        'MyData'
    """
    rules = SanitizationRules(
        strip_patterns=[],  # Don't strip any patterns
        use_pascal_case=True
    )
    return FilenameSanitizer(rules)


def create_preserve_case_sanitizer() -> FilenameSanitizer:
    """
    Create a sanitizer that preserves the original case.

    Returns:
        FilenameSanitizer that preserves case

    Example:
        >>> sanitizer = create_preserve_case_sanitizer()
        >>> sanitizer.sanitize("CustomerAccount_2025-10-09.csv")
        'CustomerAccount'
    """
    rules = SanitizationRules(use_pascal_case=False)
    return FilenameSanitizer(rules)


# Convenience function for quick sanitization

def sanitize_filename(filename: str, rules: Optional[SanitizationRules] = None) -> str:
    """
    Quick function to sanitize a single filename.

    Args:
        filename: The filename to sanitize
        rules: Optional custom sanitization rules

    Returns:
        Sanitized table name

    Example:
        >>> sanitize_filename("CustomerAccount_2025-10-09_183621.csv")
        'CustomerAccount'
    """
    sanitizer = FilenameSanitizer(rules)
    return sanitizer.sanitize(filename)


if __name__ == "__main__":
    # Demo and testing
    print("Filename Sanitizer Demo")
    print("=" * 70)

    sanitizer = FilenameSanitizer()

    test_cases = [
        "CustomerAccount_2025-10-09_183621.csv",
        "sales_data.csv",
        "Product-Info_20251009.csv",
        "employee data 2024-11-14.csv",
        "orders_v2_backup_001.csv",
        "Invoice#2024_final.csv",
        "Customer_Accounts_2024-11-14_153000.csv",
        "data.export.2024.csv",
    ]

    print("\nTest Cases:")
    print("-" * 70)
    for filename in test_cases:
        sanitized = sanitizer.sanitize(filename)
        is_valid = sanitizer.validate_table_name(sanitized)
        status = "✓" if is_valid else "✗"
        print(f"{status} {filename:50s} → {sanitized}")

    print("\n" + "=" * 70)
    print("Batch processing example:")
    print("-" * 70)
    batch_results = sanitizer.sanitize_batch(test_cases[:3])
    for original, sanitized in batch_results.items():
        print(f"  {original:50s} → {sanitized}")
