# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**load2mssql** is a production-ready Python application for loading CSV files into Microsoft SQL Server. It features dynamic metadata removal, flexible configuration via YAML, modular filename sanitization, and efficient bulk loading.

**Author**: Quentin Casares

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Mac/Linux
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Use default config.yaml
python load_csv_to_mssql.py

# Use custom configuration
python load_csv_to_mssql.py --config my_config.yaml
```

### Testing
```bash
# Test filename sanitization
python test_sanitization.py

# Run sanitizer module tests
python filename_sanitizer.py
```

## Architecture

### Core Components

**1. Main Loader (`load_csv_to_mssql.py`)**
- Entry point: `CSVToMSSQLLoader` class
- Configuration parsing using dataclasses:
  - `DatabaseConfig`: Connection settings and authentication
  - `CSVProcessingConfig`: File reading parameters
  - `FileSelectionConfig`: File filtering rules
  - `TableLoadingConfig`: Table creation and loading behavior
- Key workflow: `run()` → `get_csv_files()` → `process_file()` → `load_dataframe_to_sql()`
- Metadata handling: `read_csv_with_metadata_removal()` skips header/footer rows
- Table naming: `get_table_name()` applies custom mapping or sanitization

**2. Filename Sanitizer (`filename_sanitizer.py`)**
- **Standalone, reusable module** for transforming filenames to table names
- `FilenameSanitizer` class with configurable `SanitizationRules`
- Removes timestamps (`_20251114_093000`), dates, versions, special characters
- Converts to PascalCase by default
- SQL Server compliance validation: `validate_table_name()`
- Can be used independently: `from filename_sanitizer import sanitize_filename`

**3. Configuration (`config.yaml`)**
- YAML-based configuration with sections:
  - `database`: Server, auth mode (trusted/sql), driver, performance settings
  - `csv_processing`: Encoding, delimiter, chunk_size, metadata row skipping
  - `file_selection`: Process 'all' or 'selected' files
  - `table_loading`: if_exists strategy (fail/replace/append), schema, sanitization
  - `filename_sanitization`: PascalCase, max_length, custom patterns/replacements
  - `logging`: Level, file, format

### Data Flow

1. **Configuration Loading**: Parse `config.yaml` into dataclass configurations
2. **Database Connection**: Create SQLAlchemy engine with connection string (trusted or SQL auth)
3. **File Discovery**: Glob CSV files or filter by selected list
4. **CSV Processing**:
   - Skip header rows (`skip_header_rows`) and footer rows (`skip_footer_rows`)
   - Read with pandas using chunking for large files
5. **Table Name Resolution**:
   - Apply custom mapping if `table_naming: "custom"`
   - Otherwise use filename stem
   - Apply sanitization if `enable_sanitization: true`
6. **Bulk Loading**: Use pandas `to_sql()` with SQLAlchemy engine
   - Chunk-based inserts for memory efficiency
   - Optional dtype overrides for columns
   - Strategy: fail/replace/append
7. **Index Creation**: Post-load index creation on specified columns

### Key Design Patterns

- **Dataclasses for Configuration**: Type-safe config parsing with validation
- **Modular Sanitization**: Separate `filename_sanitizer.py` module for reusability
- **Chunked Processing**: Large CSV files processed in chunks to prevent OOM
- **Comprehensive Logging**: Dual output (console + file) with configurable levels
- **Factory Functions**: `create_timestamp_sanitizer()`, `create_simple_sanitizer()` for common patterns

## Configuration Specifics

### Authentication Modes

**Windows Authentication (Recommended)**:
```yaml
database:
  server: "localhost"
  port: 1433  # Default SQL Server port (optional)
  auth_mode: "trusted"
```

**SQL Server Authentication**:
```yaml
database:
  server: "localhost"
  port: 1433  # Specify custom port if needed
  auth_mode: "sql"
  username: "your_username"
  password: "your_password"
```

**Custom Port Configuration**:
- Default port: 1433 (standard SQL Server)
- Specify custom port for non-standard installations
- Port is optional in config (defaults to 1433)
- SQL Server connection format: `server,port` (e.g., `localhost,1434`)

### File Selection Patterns

- `mode: "all"`: Process all CSV files in `input_folder`
- `mode: "selected"`: Only process files in `selected_files` list

### Table Prefix

Add consistent prefixes to all table names (applied after sanitization):

```yaml
table_loading:
  table_prefix: "tbl_"  # All tables prefixed with "tbl_"
```

**Behavior**:
- Applied to ALL tables (both custom-mapped and filename-derived)
- Validated for SQL Server compliance (alphanumeric + underscore only)
- Truncates base name if prefix + name exceeds 128 characters
- Empty string or omit for no prefix (default)

**Examples**:
- `table_prefix: "tbl_"` → `CustomerAccount` becomes `tbl_CustomerAccount`
- `table_prefix: "stg_"` → `Sales` becomes `stg_Sales`
- `table_prefix: ""` → No prefix applied

### Table Loading Strategies

- `if_exists: "fail"`: Error if table exists (safe default for testing)
- `if_exists: "replace"`: Drop and recreate table
- `if_exists: "append"`: Add rows to existing table (for incremental loads)

### Filename Sanitization

Enabled by default (`enable_sanitization: true`). Transforms:
- `CustomerAccount_20251114_093000.csv` → `CustomerAccount`
- `sales-data-final.csv` → `SalesDataFinal`

Customize via `filename_sanitization` section:
- `use_pascal_case`: Convert to PascalCase
- `custom_patterns`: Additional regex patterns to strip
- `custom_replacements`: String replacements (e.g., "cust" → "Customer")

## Database Requirements

- **SQL Server**: 2012 or higher
- **ODBC Driver**: Version 17 or 18 for SQL Server (specified in config)
- **Permissions**: CREATE TABLE, INSERT, CREATE INDEX on target database

## Performance Optimization

### For Large Files (>100MB)
```yaml
csv_processing:
  chunk_size: 50000  # Larger chunks

database:
  fast_executemany: true  # Enable bulk insert optimization
```

### For Memory-Constrained Environments
```yaml
csv_processing:
  chunk_size: 5000  # Smaller chunks
```

## Date Formatting

All timestamps in logs use format: `YYYY-MM-DD HH:MM:SS`

Configurable via:
```yaml
logging:
  date_format: "%Y-%m-%d %H:%M:%S"
```

## Common Workflows

### Adding Custom Sanitization Patterns

1. Edit `config.yaml` under `filename_sanitization.custom_patterns`
2. Add regex pattern (e.g., `"_production$"`)
3. Test with `python test_sanitization.py`

### Creating Indexes Post-Load

```yaml
table_loading:
  table_prefix: "tbl_"  # If using prefix
  create_indexes:
    # Use base table names (without prefix) - prefix applied automatically
    CustomerAccount: ["CustomerID", "AccountNumber"]
    OrderHistory: ["OrderID"]
```

**Index Naming**:
- Format: `idx_{table}_{column}`
- Includes prefix if configured: `idx_tbl_CustomerAccount_CustomerID`
- Specify base names in config for simplicity

**Note**: The system automatically looks up indexes by base name, so you don't need to include the prefix in the `create_indexes` configuration.

### Handling Schema Changes

- Use `dtype_overrides` to force specific SQL Server data types
- Format: `table_name: {column: "SQL_TYPE"}`

Example:
```yaml
table_loading:
  dtype_overrides:
    Sales:
      OrderDate: "DATETIME"
      Amount: "DECIMAL(18,2)"
```

## Module Reusability

The `filename_sanitizer.py` module can be used standalone in other projects:

```python
from filename_sanitizer import FilenameSanitizer, SanitizationRules

# Quick usage
sanitizer = FilenameSanitizer()
table_name = sanitizer.sanitize("file_20251114.csv")

# Custom rules
rules = SanitizationRules(
    use_pascal_case=False,
    custom_replacements={"acct": "Account"}
)
sanitizer = FilenameSanitizer(rules)
```

## Error Handling

- **Connection Errors**: Check ODBC driver installation and config credentials
- **CSV Parsing Errors**: Verify encoding, delimiter, and metadata row counts
- **Table Exists**: Use `if_exists: "fail"` to prevent accidental overwrites
- **Invalid Table Names**: Sanitizer validates against SQL Server naming rules

## Security Notes

- Never commit `config.yaml` with credentials to version control
- Use `.gitignore` to exclude sensitive configs
- Prefer Windows Authentication (`auth_mode: "trusted"`) when available
- Use environment variables for sensitive data in production
