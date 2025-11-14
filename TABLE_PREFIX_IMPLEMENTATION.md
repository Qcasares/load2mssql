# Table Prefix Implementation

**Author**: Quentin Casares
**Date**: 20251114

## Overview

Added configurable table prefix functionality to allow consistent prefixing of all table names (e.g., "tbl_", "stg_", "dim_").

## What Was Implemented

### 1. Configuration (config.yaml)

Added `table_prefix` parameter to the `table_loading` section:

```yaml
table_loading:
  table_prefix: "tbl_"  # Empty string "" for no prefix (default)
```

**Behavior**:
- Applied to ALL tables (both custom-mapped and filename-derived)
- Strict validation: alphanumeric characters and underscores only
- Auto-sanitizes invalid characters
- Truncates base name if total length exceeds 128 characters (preserves full prefix)

### 2. Code Changes

**Modified Files**:
- `config.yaml` - Added table_prefix configuration option
- `load_csv_to_mssql.py` - Core implementation (7 locations)
- `CLAUDE.md` - Updated documentation

**Key Changes in load_csv_to_mssql.py**:

1. **Line 81**: Added `table_prefix: str = ""` to `TableLoadingConfig` dataclass
2. **Line 91**: Added prefix normalization in `__post_init__`
3. **Line 219**: Parse `table_prefix` from YAML config
4. **Line 258-287**: New `_sanitize_prefix()` method with strict validation
5. **Line 466-489**: Apply prefix in `get_table_name()` with length handling
6. **Line 548-578**: Update `create_indexes()` to support base name lookup

### 3. Prefix Application Flow

```
1. Custom table name mapping (if enabled)
   ↓
2. Filename sanitization (if enabled)
   ↓
3. Prefix application:
   - Sanitize prefix (remove invalid chars)
   - Check length (max 128 total)
   - Truncate base name if needed (preserve prefix)
   - Apply prefix
   ↓
4. Final validation
   ↓
5. Table creation in SQL Server
```

### 4. Validation Rules

**Prefix Sanitization** (strict mode):
- Only alphanumeric characters and underscores allowed
- Invalid characters removed automatically
- If starts with digit, prepend underscore
- Logged if modified from original

**Length Handling**:
- SQL Server limit: 128 characters
- Calculation: `max_base_length = 128 - len(prefix)`
- Base name truncated to fit if necessary
- Full prefix always preserved

### 5. Index Creation

Indexes automatically work with prefixed table names:

**Config Example**:
```yaml
table_loading:
  table_prefix: "tbl_"
  create_indexes:
    CustomerAccount: ["CustomerID"]  # Use base name
```

**Result**:
- Index created on `tbl_CustomerAccount` table
- Index named: `idx_tbl_CustomerAccount_CustomerID`

**Lookup Logic**:
1. Try full name first: `tbl_CustomerAccount`
2. If not found, extract base name: `CustomerAccount`
3. Look up by base name for backward compatibility

## Examples

### Example 1: Standard Prefix

**Config**:
```yaml
table_loading:
  table_prefix: "tbl_"
  enable_sanitization: true
```

**Results**:
- `CustomerAccount_20251114_093000.csv` → `tbl_CustomerAccount`
- `OrderHistory_2025-10-09_183621.csv` → `tbl_OrderHistory`
- `sales_data.csv` → `tbl_SalesData`

### Example 2: Staging Environment

**Config**:
```yaml
table_loading:
  table_prefix: "stg_"
  enable_sanitization: true
```

**Results**:
- `CustomerAccount_20251114_093000.csv` → `stg_CustomerAccount`
- `sales_data.csv` → `stg_SalesData`

### Example 3: No Prefix (Default)

**Config**:
```yaml
table_loading:
  table_prefix: ""  # or omit entirely
```

**Results**:
- `CustomerAccount_20251114_093000.csv` → `CustomerAccount`
- `sales_data.csv` → `SalesData`

### Example 4: Custom Names with Prefix

**Config**:
```yaml
table_loading:
  table_prefix: "tbl_"
  table_naming: "custom"
  custom_table_names:
    "sales_data.csv": "Sales"
    "customer_info.csv": "Customers"
```

**Results**:
- `sales_data.csv` → `tbl_Sales`
- `customer_info.csv` → `tbl_Customers`

## Testing

### Test Files Created

1. **test_prefix_simple.py**: Standalone test for prefix sanitization
   - Tests 11 different prefix scenarios
   - No dependencies required
   - All tests passing ✓

2. **config_with_prefix_example.yaml**: Example configuration
   - Shows prefix usage with all features
   - Documents best practices
   - Ready to use as template

### Test Results

```
Table Prefix Sanitization Test
================================================================================

✓ Valid prefix with underscore       (tbl_ → tbl_)
✓ Valid prefix word with underscore  (staging_ → staging_)
✓ Short valid prefix                 (dim_ → dim_)
✓ Prefix starting with number        (123_ → _123_)
✓ Invalid character - removed        (tbl-test → tbltest)
✓ Invalid character @ removed        (tbl@test → tbltest)
✓ Space removed                      (tbl test → tbltest)
✓ Dot removed                        (tbl.test → tbltest)
✓ Leading $ removed                  ($tbl_ → tbl_)
✓ Empty prefix                       ("" → "")
✓ Valid alphanumeric with underscores (test_123_ → test_123_)

Results: 11 passed, 0 failed
```

## Backward Compatibility

- **Default value**: Empty string (`""`) - no prefix applied
- **Existing configs**: Continue to work without modification
- **Index configs**: Support both base names and full names
- **No breaking changes**: All existing functionality preserved

## Usage Instructions

### Basic Usage

1. Edit `config.yaml`
2. Set `table_prefix` under `table_loading` section:
   ```yaml
   table_loading:
     table_prefix: "tbl_"
   ```
3. Run the loader as normal:
   ```bash
   python load_csv_to_mssql.py
   ```

### Recommended Prefixes

- **Production tables**: `tbl_` (standard convention)
- **Staging/import**: `stg_` or `staging_`
- **Data warehouse**: `dim_`, `fact_`, `bridge_`
- **Temporary**: `tmp_` or `temp_`
- **Development**: `dev_`

### Best Practices

1. **Use consistent prefixes** across environments
2. **Keep prefixes short** (3-5 characters) to maximize table name length
3. **Document prefix meaning** in your team's conventions
4. **Use base names in configs** for `create_indexes` and `dtype_overrides`
5. **Test prefix changes** in non-production first

## Logging Examples

### With Prefix Applied

```
INFO - Sanitized table name: 'CustomerAccount_2025-10-09_183621' → 'CustomerAccount'
INFO - Applied table prefix: 'CustomerAccount' → 'tbl_CustomerAccount'
INFO - Loading 150 rows into [dbo].[tbl_CustomerAccount] (mode: replace)
INFO - Successfully loaded data into tbl_CustomerAccount
```

### With Invalid Prefix Characters

```
WARNING - Table prefix sanitized for SQL Server compliance: 'tbl-test' → 'tbltest'
INFO - Applied table prefix: 'CustomerAccount' → 'tbltestCustomerAccount'
```

### With Length Truncation

```
WARNING - Table name 'VeryLongTableNameThatExceedsMaximumLength...' is too long with prefix 'tbl_'. Truncating base name from 125 to 124 characters.
INFO - Applied table prefix: 'VeryLongTableName...' → 'tbl_VeryLongTableName...'
```

## Future Enhancements

Potential improvements for future versions:

1. **Environment-based prefixes**: Load prefix from environment variable
2. **Prefix templates**: Dynamic prefixes like `{env}_{type}_` → `prod_tbl_`
3. **Validation warnings**: Detect potential prefix collisions
4. **Prefix removal**: Option to strip existing prefixes before applying new ones
5. **Per-file prefixes**: Different prefixes for different file patterns

## Questions & Support

For questions or issues with table prefix functionality:

1. Check `CLAUDE.md` for configuration details
2. Review `config_with_prefix_example.yaml` for examples
3. Run `python test_prefix_simple.py` to verify functionality
4. Check logs for prefix application details
