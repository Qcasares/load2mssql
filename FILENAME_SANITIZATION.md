# Filename Sanitization

This document explains the modular filename sanitization feature for the CSV to MS SQL Server loader.

## Overview

The filename sanitizer is a reusable module that transforms CSV filenames into clean, SQL Server-compliant table names. It automatically handles:

- **Timestamps and dates**: Removes patterns like `_2025-10-09_183621` or `_20251114`
- **Special characters**: Converts hyphens, spaces, and dots to underscores or removes them
- **Version suffixes**: Strips patterns like `_v1`, `_final`, `_backup`
- **Case normalization**: Converts to PascalCase for consistency
- **SQL Server compliance**: Ensures table names meet SQL Server naming requirements

## Quick Start

### Basic Usage

The sanitizer is automatically integrated into the CSV loader. By default, it's enabled and will sanitize all filenames:

```bash
# Files like this:
CustomerAccount_2025-10-09_183621.csv
OrderHistory_20251114_093000.csv
sales_data.csv

# Become table names like this:
CustomerAccount
OrderHistory
SalesData
```

### Configuration

Enable or disable sanitization in `config.yaml`:

```yaml
table_loading:
  enable_sanitization: true  # Set to false to disable
```

### Advanced Configuration

Customize sanitization behavior:

```yaml
filename_sanitization:
  # Convert to PascalCase (true) or preserve case (false)
  use_pascal_case: true

  # Maximum table name length (SQL Server limit: 128)
  max_length: 128

  # Add custom patterns to strip
  custom_patterns:
    - "_production$"
    - "_staging$"
    - "_export$"

  # Add custom replacements
  custom_replacements:
    "cust": "Customer"
    "acct": "Account"
    "prod": "Product"
```

## Module API

### Using the Sanitizer Standalone

You can use the sanitizer module independently:

```python
from filename_sanitizer import FilenameSanitizer

# Create sanitizer
sanitizer = FilenameSanitizer()

# Sanitize a single filename
table_name = sanitizer.sanitize("CustomerAccount_2025-10-09_183621.csv")
# Result: "CustomerAccount"

# Sanitize multiple files
filenames = [
    "CustomerAccount_2025-10-09_183621.csv",
    "OrderHistory_20251114_093000.csv",
    "sales_data.csv"
]
results = sanitizer.sanitize_batch(filenames)
# Result: {
#     "CustomerAccount_2025-10-09_183621.csv": "CustomerAccount",
#     "OrderHistory_20251114_093000.csv": "OrderHistory",
#     "sales_data.csv": "SalesData"
# }

# Validate a table name
is_valid = sanitizer.validate_table_name("CustomerAccount")
# Result: True
```

### Custom Sanitization Rules

Create a sanitizer with custom rules:

```python
from filename_sanitizer import FilenameSanitizer, SanitizationRules

# Define custom rules
rules = SanitizationRules(
    use_pascal_case=True,
    max_length=64,  # Shorter max length
    custom_replacements={
        "cust": "Customer",
        "acct": "Account"
    }
)

# Create sanitizer with custom rules
sanitizer = FilenameSanitizer(rules)

# Add dynamic patterns
sanitizer.add_custom_pattern(r"_export$")
sanitizer.add_custom_replacement(r"prod", "Product")

# Use it
table_name = sanitizer.sanitize("cust_acct_export.csv")
# Result: "CustomerAccount"
```

### Pre-configured Sanitizers

Use pre-configured sanitizers for common scenarios:

```python
from filename_sanitizer import (
    create_timestamp_sanitizer,
    create_simple_sanitizer,
    create_preserve_case_sanitizer
)

# Optimized for timestamped filenames (default)
timestamp_sanitizer = create_timestamp_sanitizer()

# Minimal processing - just removes extension and normalizes
simple_sanitizer = create_simple_sanitizer()

# Preserves original case
preserve_case = create_preserve_case_sanitizer()
```

### Quick Function

For one-off sanitization:

```python
from filename_sanitizer import sanitize_filename

# Quick sanitization with defaults
table_name = sanitize_filename("CustomerAccount_2025-10-09_183621.csv")
# Result: "CustomerAccount"

# With custom rules
from filename_sanitizer import SanitizationRules

rules = SanitizationRules(use_pascal_case=False)
table_name = sanitize_filename("sales_data.csv", rules)
# Result: "sales_data"
```

## Sanitization Patterns

The sanitizer automatically removes these patterns:

### Timestamp Patterns
- `_YYYY-MM-DD_HHMMSS` → `_2025-10-09_183621`
- `_YYYYMMDD_HHMMSS` → `_20251009_183621`

### Date Patterns
- `_YYYY-MM-DD` → `_2025-10-09`
- `_YYYYMMDD` → `_20251009`
- `_MMDDYYYY` → `_10092025`

### Time Patterns
- `_HHMMSS` → `_183621`
- `_HH-MM-SS` → `_18-36-21`

### Version Patterns
- `_v1`, `_v2.0` → Version indicators
- `_ver1`, `_version1` → Verbose versions

### Common Suffixes
- `_final`, `_backup`, `_temp`, `_copy`, `_old`, `_new`

### Sequential Numbers
- `_001`, `_1`, `_01` → Trailing numbers

## Examples

### Example 1: Timestamped Files

**Input files:**
```
CustomerAccount_2025-10-09_183621.csv
OrderHistory_20251114_093000.csv
Products_2024-12-01_120000.csv
```

**Resulting table names:**
```
CustomerAccount
OrderHistory
Products
```

### Example 2: Mixed Naming Conventions

**Input files:**
```
sales-data-2024.csv
customer_info_v2.csv
Product Info (Final).csv
employee.data.backup.001.csv
```

**Resulting table names:**
```
SalesData2024
CustomerInfo
ProductInfoFinal
EmployeeDataBackup
```

### Example 3: Custom Patterns

**Configuration:**
```yaml
filename_sanitization:
  custom_patterns:
    - "_production$"
    - "_staging$"
  custom_replacements:
    "cust": "Customer"
    "dept": "Department"
```

**Input files:**
```
cust_accounts_production.csv
dept_sales_staging.csv
```

**Resulting table names:**
```
CustomerAccounts
DepartmentSales
```

## Testing

### Test Your Filenames

Use the included test script to see how your filenames will be sanitized:

```bash
python test_sanitization.py
```

**Example output:**
```
Filename Sanitization Test
================================================================================

Found 5 CSV file(s) to process:

✓ CustomerAccount_2025-10-09_183621.csv              → CustomerAccount
✓ OrderHistory_20251114_093000.csv                   → OrderHistory
✓ customers.csv                                      → Customers
✓ products.csv                                       → Products
✓ sales_data.csv                                     → SalesData

================================================================================
Summary:
--------------------------------------------------------------------------------
Total files:     5
Valid names:     5
Invalid names:   0
```

### Unit Tests

Test the module directly:

```bash
python filename_sanitizer.py
```

This runs the built-in demo with various test cases.

## SQL Server Naming Rules

The sanitizer ensures table names comply with SQL Server requirements:

- **Must start with**: Letter, underscore (`_`), at sign (`@`), or hash (`#`)
- **Can contain**: Letters, digits, underscore, at sign, dollar sign (`$`), hash
- **Maximum length**: 128 characters
- **Cannot be**: SQL Server reserved keywords (simplified check)

Invalid characters are automatically removed or replaced.

## Integration with CSV Loader

The sanitizer is seamlessly integrated into the main CSV loader:

### In `load_csv_to_mssql.py`

```python
# Initialization
self.sanitizer = self._setup_sanitizer()

# Getting table names
def get_table_name(self, csv_filename: str) -> str:
    # ... determine base table name ...

    # Apply sanitization if enabled
    if self.table_config.enable_sanitization:
        table_name = self.sanitizer.sanitize(csv_filename)
        # Logs: "Sanitized table name: 'original' → 'sanitized'"

    return table_name
```

### Logging

When sanitization changes a filename, you'll see log entries like:

```
INFO - Sanitized table name: 'CustomerAccount_2025-10-09_183621' → 'CustomerAccount'
INFO - Loading 5 rows into [dbo].[CustomerAccount] (mode: replace)
```

## Best Practices

1. **Enable by default**: Keep sanitization enabled for production data with timestamps
2. **Test first**: Use `test_sanitization.py` to preview table names before loading
3. **Custom patterns**: Add organization-specific patterns to the config
4. **Validate names**: The sanitizer validates names but always test with your SQL Server version
5. **Preserve case option**: Use `use_pascal_case: false` if you need to preserve original casing
6. **Custom mapping**: For specific files, use the `custom_table_names` config option instead

## Troubleshooting

### Table name is not what I expected

Check the sanitization patterns and rules. Run the test script to see the transformation:

```bash
python test_sanitization.py
```

### Want to disable sanitization for specific files

Use custom table name mapping:

```yaml
table_loading:
  table_naming: "custom"
  custom_table_names:
    "special_file_2024.csv": "SpecialFile2024"  # Keeps the date
```

### Need different sanitization rules

Customize the `filename_sanitization` section in `config.yaml`:

```yaml
filename_sanitization:
  use_pascal_case: false  # Preserve original case
  custom_patterns:
    - "YOUR_PATTERN_HERE"
```

### Table name conflicts

If multiple timestamped files sanitize to the same table name:
```
Orders_2025-01-01_120000.csv → Orders
Orders_2025-01-02_120000.csv → Orders
```

Use append mode to combine them:
```yaml
table_loading:
  if_exists: "append"
```

Or disable sanitization and use the full filename as table name.

## Module Architecture

### Files

- `filename_sanitizer.py` - Main sanitization module (standalone, reusable)
- `load_csv_to_mssql.py` - CSV loader (integrates the sanitizer)
- `test_sanitization.py` - Testing utility
- `config.yaml` - Configuration file

### Classes

- `SanitizationRules` - Configuration dataclass for sanitization rules
- `FilenameSanitizer` - Main sanitizer class with all logic

### Key Methods

- `sanitize(filename)` - Sanitize a single filename
- `sanitize_batch(filenames)` - Sanitize multiple filenames
- `validate_table_name(name)` - Validate SQL Server compliance
- `add_custom_pattern(pattern)` - Add patterns dynamically
- `add_custom_replacement(pattern, replacement)` - Add replacements dynamically

## License

MIT License - Same as the parent project

## Author

Claude (Anthropic)
