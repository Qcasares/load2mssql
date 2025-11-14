# CSV to Microsoft SQL Server Loader

A robust, production-ready Python script for dynamically loading CSV files into Microsoft SQL Server with support for metadata removal, flexible configuration, and efficient bulk loading.

## Features

- **Dynamic Metadata Removal**: Automatically skip header and footer rows containing metadata
- **Flexible Authentication**: Support for both Windows (Trusted) and SQL Server authentication
- **Configurable File Selection**: Load all CSV files or only specific files via YAML configuration
- **Efficient Processing**: Chunked reading for large files to prevent memory issues
- **Bulk Loading**: Optimized bulk insert operations using SQLAlchemy and pyodbc
- **Type Management**: Automatic type inference with optional custom data type overrides
- **Index Creation**: Automatically create indexes on specified columns after loading
- **Multiple Load Strategies**: Replace, append, or fail on existing tables
- **Comprehensive Logging**: Detailed logging to both console and file
- **Error Handling**: Robust error handling with detailed error messages
- **Pythonic & Modern**: Uses type hints, dataclasses, and modern Python practices

## Requirements

- Python 3.8 or higher
- Microsoft SQL Server (2012 or higher)
- ODBC Driver for SQL Server (17 or 18 recommended)
- Windows or Linux operating system

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd load2mssql
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install ODBC Driver

**Windows:**
- Download and install [Microsoft ODBC Driver 17 or 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

**Linux (Ubuntu/Debian):**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**Linux (RHEL/CentOS):**
```bash
curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo
yum remove unixODBC-utf16 unixODBC-utf16-devel
ACCEPT_EULA=Y yum install -y msodbcsql17
```

## Configuration

### Basic Configuration

Edit `config.yaml` to match your environment:

```yaml
database:
  server: "localhost"
  database: "YourDatabase"
  auth_mode: "trusted"  # Use Windows Authentication
  driver: "ODBC Driver 17 for SQL Server"

csv_processing:
  input_folder: "./csv_files"
  skip_header_rows: 2  # Skip first 2 rows (metadata)
  skip_footer_rows: 1  # Skip last row (metadata)
  encoding: "utf-8"
  delimiter: ","

file_selection:
  mode: "all"  # Process all CSV files
```

### Advanced Configuration Options

#### Database Authentication

**Windows Authentication (Trusted):**
```yaml
database:
  auth_mode: "trusted"
```

**SQL Server Authentication:**
```yaml
database:
  auth_mode: "sql"
  username: "your_username"
  password: "your_password"
```

#### File Selection Modes

**Load All Files:**
```yaml
file_selection:
  mode: "all"
```

**Load Specific Files:**
```yaml
file_selection:
  mode: "selected"
  selected_files:
    - "sales_2024.csv"
    - "customers.csv"
```

#### Table Loading Strategies

```yaml
table_loading:
  if_exists: "replace"  # Options: 'replace', 'append', 'fail'
  schema: "dbo"
  table_naming: "filename"  # Use CSV filename as table name
```

#### Custom Table Names

```yaml
table_loading:
  table_naming: "custom"
  custom_table_names:
    "sales_data.csv": "Sales"
    "customer_info.csv": "Customers"
```

#### Create Indexes

```yaml
table_loading:
  create_indexes:
    Sales: ["OrderID", "CustomerID"]
    Customers: ["CustomerID"]
```

#### Data Type Overrides

```yaml
table_loading:
  dtype_overrides:
    Sales:
      OrderID: "INT"
      OrderDate: "DATETIME"
      Amount: "DECIMAL(18,2)"
```

## Usage

### Basic Usage

```bash
python load_csv_to_mssql.py
```

### Using Custom Configuration File

```bash
python load_csv_to_mssql.py --config my_config.yaml
```

### Command Line Options

```bash
python load_csv_to_mssql.py --help
```

## CSV File Structure

### Example CSV with Metadata

```csv
Report Generated: 2024-01-15
Data Source: Sales System
OrderID,CustomerID,OrderDate,Amount
1001,C001,2024-01-01,1500.50
1002,C002,2024-01-02,2300.75
1003,C001,2024-01-03,500.25
Total Records: 3
```

### Configuration for Above CSV

```yaml
csv_processing:
  skip_header_rows: 2  # Skip "Report Generated" and "Data Source"
  skip_footer_rows: 1  # Skip "Total Records"
```

## Directory Structure

```
load2mssql/
├── load_csv_to_mssql.py    # Main script
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── csv_files/              # Default CSV input folder
│   ├── sales.csv
│   ├── customers.csv
│   └── products.csv
└── csv_loader.log          # Log file (generated)
```

## Logging

The script provides comprehensive logging:

- **Console Output**: Real-time progress and status updates
- **Log File**: Detailed logs saved to `csv_loader.log` (configurable)

### Log Levels

Configure in `config.yaml`:

```yaml
logging:
  level: "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_file: "csv_loader.log"
```

## Error Handling

The script handles various error scenarios:

- **Missing Configuration**: Clear error if config file not found
- **Database Connection Errors**: Detailed connection failure messages
- **CSV Parsing Errors**: Reports which file failed and why
- **SQL Errors**: Captures and logs SQL-related errors
- **File Not Found**: Warns about missing selected files

## Performance Optimization

### For Large Files

```yaml
csv_processing:
  chunk_size: 50000  # Increase for better performance with large files

database:
  fast_executemany: true  # Enable fast bulk insert
```

### For Many Small Files

```yaml
csv_processing:
  chunk_size: 10000  # Smaller chunks for better memory management
```

## Examples

### Example 1: Load All CSV Files

```yaml
file_selection:
  mode: "all"
```

```bash
python load_csv_to_mssql.py
```

### Example 2: Load Specific Files with Custom Table Names

```yaml
file_selection:
  mode: "selected"
  selected_files:
    - "sales_jan.csv"
    - "sales_feb.csv"

table_loading:
  table_naming: "custom"
  custom_table_names:
    "sales_jan.csv": "Sales_January"
    "sales_feb.csv": "Sales_February"
```

### Example 3: Append to Existing Tables

```yaml
table_loading:
  if_exists: "append"  # Add to existing data
```

### Example 4: Skip Metadata Rows

For CSV files with 3 header metadata rows and 2 footer rows:

```yaml
csv_processing:
  skip_header_rows: 3
  skip_footer_rows: 2
```

## Troubleshooting

### Connection Issues

**Error: "Data source name not found"**
- Verify ODBC driver is installed
- Check driver name in config matches installed driver
- Run `odbcinst -q -d` (Linux) or check ODBC Data Source Administrator (Windows)

**Error: "Login failed"**
- Verify SQL Server authentication credentials
- For trusted authentication, ensure Windows user has SQL Server access

### CSV Parsing Issues

**Error: "Unable to open file"**
- Verify file path in configuration
- Check file permissions
- Ensure file encoding matches configuration

**Error: "No columns to parse"**
- Check `skip_header_rows` value isn't too large
- Verify CSV delimiter is correct

### Performance Issues

**Slow loading speed:**
- Increase `chunk_size` in configuration
- Enable `fast_executemany` in database config
- Reduce number of indexes created during load

**Out of memory errors:**
- Decrease `chunk_size`
- Process fewer files at once

## Best Practices

1. **Test First**: Use `if_exists: "fail"` initially to avoid overwriting data
2. **Backup Data**: Always backup your database before bulk operations
3. **Use Virtual Environment**: Isolate dependencies in a virtual environment
4. **Log Everything**: Keep logging enabled for troubleshooting
5. **Validate Data**: Check loaded data with SQL queries after loading
6. **Incremental Loading**: Use `if_exists: "append"` for incremental loads
7. **Index After Load**: Create indexes after loading for better performance
8. **Secure Credentials**: Never commit config files with passwords to git

## Security Considerations

- **Use Trusted Authentication**: Prefer Windows Authentication when possible
- **Protect Config Files**: Add config files with credentials to `.gitignore`
- **Use Environment Variables**: Consider using environment variables for sensitive data
- **Restrict Database Permissions**: Use SQL Server accounts with minimum required permissions
- **Audit Logs**: Regularly review log files for unusual activity

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure code follows PEP 8 style guide
5. Update documentation
6. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review log files for detailed error information

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial release
- Support for metadata removal
- Configurable file selection
- Multiple authentication modes
- Comprehensive logging
- Index creation support
- Custom data type mapping

## Acknowledgments

Built with:
- [pandas](https://pandas.pydata.org/) - Data manipulation and analysis
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [pyodbc](https://github.com/mkleehammer/pyodbc) - ODBC database connectivity
- [PyYAML](https://pyyaml.org/) - YAML parser

## Authors

- Claude - Initial implementation and documentation
