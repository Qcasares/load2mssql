# Example CSV Files

This folder contains example CSV files to demonstrate the functionality of the CSV to MS SQL Server Loader.

## Files Included

### 1. sales_data.csv
- **Purpose**: Sample sales transactions data
- **Metadata**: 2 header rows, 1 footer row
- **Columns**: OrderID, CustomerID, OrderDate, ProductName, Quantity, UnitPrice, TotalAmount
- **Rows**: 10 data rows
- **Configuration Needed**:
  ```yaml
  csv_processing:
    skip_header_rows: 2
    skip_footer_rows: 1
  ```

### 2. customers.csv
- **Purpose**: Customer information
- **Metadata**: 2 header rows, 1 footer row
- **Columns**: CustomerID, FirstName, LastName, Email, Phone, City, State, Country, JoinDate
- **Rows**: 5 data rows
- **Configuration Needed**:
  ```yaml
  csv_processing:
    skip_header_rows: 2
    skip_footer_rows: 1
  ```

### 3. products.csv
- **Purpose**: Product catalog
- **Metadata**: None (clean CSV)
- **Columns**: ProductID, ProductName, Category, SupplierID, UnitPrice, UnitsInStock, ReorderLevel
- **Rows**: 10 data rows
- **Configuration Needed**:
  ```yaml
  csv_processing:
    skip_header_rows: 0
    skip_footer_rows: 0
  ```

## Using These Files

To test the loader with these example files:

1. Ensure your SQL Server is running and accessible
2. Update `config.yaml` with your database connection details
3. Configure metadata skipping as needed for your files
4. Run the loader:
   ```bash
   python load_csv_to_mssql.py
   ```

## Adding Your Own Files

1. Place your CSV files in this folder
2. Update `config.yaml` to specify:
   - Number of header rows to skip
   - Number of footer rows to skip
   - File encoding if different from UTF-8
   - Delimiter if different from comma
3. Run the loader

## Notes

- The example files use comma (`,`) as delimiter
- All files are UTF-8 encoded
- Date formats follow ISO standard (YYYY-MM-DD)
- Some files contain metadata headers/footers to demonstrate the removal feature
