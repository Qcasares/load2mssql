#!/usr/bin/env python3
"""
CSV to Microsoft SQL Server Loader
===================================

A robust, production-ready script for loading CSV files into Microsoft SQL Server
with support for metadata removal, flexible configuration, and efficient bulk loading.

Features:
    - Dynamic metadata header/footer removal
    - Trusted (Windows) or SQL Server authentication
    - Configurable file selection (all or specific files)
    - Chunked processing for large files
    - Comprehensive logging and error handling
    - Type inference and custom data type mapping
    - Index creation support
    - Multiple loading strategies (replace, append, fail)

Author: Claude
License: MIT
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import quote_plus

import pandas as pd
import yaml
from sqlalchemy import create_engine, text, inspect, Index
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import pyodbc

from filename_sanitizer import FilenameSanitizer, SanitizationRules


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    server: str
    database: str
    auth_mode: str
    driver: str
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    fast_executemany: bool = True


@dataclass
class CSVProcessingConfig:
    """CSV file processing configuration."""
    input_folder: Path
    skip_header_rows: int = 0
    skip_footer_rows: int = 0
    encoding: str = "utf-8"
    delimiter: str = ","
    chunk_size: int = 10000


@dataclass
class FileSelectionConfig:
    """File selection configuration."""
    mode: str  # 'all' or 'selected'
    selected_files: List[str]


@dataclass
class TableLoadingConfig:
    """Table loading configuration."""
    if_exists: str  # 'fail', 'replace', 'append'
    schema: str = "dbo"
    table_naming: str = "filename"  # 'filename' or 'custom'
    custom_table_names: Dict[str, str] = None
    create_indexes: Dict[str, List[str]] = None
    dtype_overrides: Dict[str, Dict[str, str]] = None
    enable_sanitization: bool = True
    table_prefix: str = ""  # Prefix to add to all table names (e.g., "tbl_")

    def __post_init__(self):
        if self.custom_table_names is None:
            self.custom_table_names = {}
        if self.create_indexes is None:
            self.create_indexes = {}
        if self.dtype_overrides is None:
            self.dtype_overrides = {}
        # Normalize table_prefix (treat None as empty string)
        if self.table_prefix is None:
            self.table_prefix = ""


class CSVToMSSQLLoader:
    """
    Main class for loading CSV files into Microsoft SQL Server.

    This class handles the entire ETL process:
    - Reading and validating configuration
    - Establishing database connections
    - Processing CSV files with metadata removal
    - Loading data into SQL Server tables
    - Creating indexes and applying optimizations
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the loader with configuration.

        Args:
            config_path: Path to the YAML configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.engine: Optional[Engine] = None

        # Parse configuration sections
        self.db_config = self._parse_db_config()
        self.csv_config = self._parse_csv_config()
        self.file_config = self._parse_file_config()
        self.table_config = self._parse_table_config()

        # Initialize filename sanitizer
        self.sanitizer = self._setup_sanitizer()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load and validate the YAML configuration file.

        Returns:
            Dictionary containing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _setup_logging(self) -> None:
        """Configure logging based on configuration settings."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        date_format = log_config.get('date_format', '%Y-%m-%d %H:%M:%S')

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )

        # Add file handler if specified
        log_file = log_config.get('log_file')
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            logging.getLogger().addHandler(file_handler)

    def _parse_db_config(self) -> DatabaseConfig:
        """Parse database configuration section."""
        db = self.config['database']
        return DatabaseConfig(
            server=db['server'],
            database=db['database'],
            auth_mode=db['auth_mode'],
            driver=db['driver'],
            username=db.get('username'),
            password=db.get('password'),
            timeout=db.get('timeout', 30),
            fast_executemany=db.get('fast_executemany', True)
        )

    def _parse_csv_config(self) -> CSVProcessingConfig:
        """Parse CSV processing configuration section."""
        csv = self.config['csv_processing']
        return CSVProcessingConfig(
            input_folder=Path(csv['input_folder']),
            skip_header_rows=csv.get('skip_header_rows', 0),
            skip_footer_rows=csv.get('skip_footer_rows', 0),
            encoding=csv.get('encoding', 'utf-8'),
            delimiter=csv.get('delimiter', ','),
            chunk_size=csv.get('chunk_size', 10000)
        )

    def _parse_file_config(self) -> FileSelectionConfig:
        """Parse file selection configuration section."""
        fs = self.config['file_selection']
        return FileSelectionConfig(
            mode=fs['mode'],
            selected_files=fs.get('selected_files', [])
        )

    def _parse_table_config(self) -> TableLoadingConfig:
        """Parse table loading configuration section."""
        tl = self.config['table_loading']
        return TableLoadingConfig(
            if_exists=tl['if_exists'],
            schema=tl.get('schema', 'dbo'),
            table_naming=tl.get('table_naming', 'filename'),
            custom_table_names=tl.get('custom_table_names', {}),
            create_indexes=tl.get('create_indexes', {}),
            dtype_overrides=tl.get('dtype_overrides', {}),
            enable_sanitization=tl.get('enable_sanitization', True),
            table_prefix=tl.get('table_prefix', '')
        )

    def _setup_sanitizer(self) -> FilenameSanitizer:
        """
        Setup filename sanitizer based on configuration.

        Returns:
            Configured FilenameSanitizer instance
        """
        # Get sanitization config if it exists
        sanitization_config = self.config.get('filename_sanitization', {})

        # Build sanitization rules
        rules_kwargs = {}

        if 'use_pascal_case' in sanitization_config:
            rules_kwargs['use_pascal_case'] = sanitization_config['use_pascal_case']

        if 'max_length' in sanitization_config:
            rules_kwargs['max_length'] = sanitization_config['max_length']

        if 'custom_patterns' in sanitization_config:
            rules_kwargs['strip_patterns'] = SanitizationRules().strip_patterns + sanitization_config['custom_patterns']

        if 'custom_replacements' in sanitization_config:
            rules_kwargs['custom_replacements'] = sanitization_config['custom_replacements']

        # Create sanitization rules
        if rules_kwargs:
            rules = SanitizationRules(**rules_kwargs)
            sanitizer = FilenameSanitizer(rules)
        else:
            # Use default sanitizer
            sanitizer = FilenameSanitizer()

        self.logger.debug("Filename sanitizer initialized")
        return sanitizer

    def _sanitize_prefix(self, prefix: str) -> str:
        """
        Sanitize and validate table prefix for SQL Server compliance.

        Only allows alphanumeric characters and underscores (strict mode).
        If prefix starts with a digit, prepends an underscore.

        Args:
            prefix: Raw prefix from configuration

        Returns:
            Sanitized prefix safe for SQL Server
        """
        if not prefix:
            return ""

        # Remove all characters except alphanumeric and underscore (strict mode)
        sanitized = re.sub(r'[^\w]', '', prefix)

        # Ensure prefix doesn't start with a digit
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized

        # Log if prefix was modified
        if sanitized != prefix:
            self.logger.warning(
                f"Table prefix sanitized for SQL Server compliance: '{prefix}' → '{sanitized}'"
            )

        return sanitized

    def _create_connection_string(self) -> str:
        """
        Create SQL Server connection string based on authentication mode.

        Returns:
            SQLAlchemy connection string
        """
        db = self.db_config
        driver = quote_plus(db.driver)

        if db.auth_mode.lower() == 'trusted':
            # Windows Authentication
            conn_str = (
                f"mssql+pyodbc://@{db.server}/{db.database}"
                f"?driver={driver}&Trusted_Connection=yes"
                f"&timeout={db.timeout}"
            )
        else:
            # SQL Server Authentication
            if not db.username or not db.password:
                raise ValueError("Username and password required for SQL Server authentication")

            username = quote_plus(db.username)
            password = quote_plus(db.password)
            conn_str = (
                f"mssql+pyodbc://{username}:{password}@{db.server}/{db.database}"
                f"?driver={driver}&timeout={db.timeout}"
            )

        return conn_str

    def connect_database(self) -> None:
        """
        Establish database connection.

        Raises:
            SQLAlchemyError: If connection fails
        """
        try:
            conn_str = self._create_connection_string()

            # Create engine with optimizations
            connect_args = {}
            if self.db_config.fast_executemany:
                connect_args['fast_executemany'] = True

            self.engine = create_engine(
                conn_str,
                connect_args=connect_args,
                pool_pre_ping=True,  # Verify connections before using
                echo=False
            )

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.logger.info(
                f"Successfully connected to {self.db_config.server}/{self.db_config.database}"
            )

        except SQLAlchemyError as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def get_csv_files(self) -> List[Path]:
        """
        Get list of CSV files to process based on configuration.

        Returns:
            List of Path objects for CSV files

        Raises:
            FileNotFoundError: If input folder doesn't exist
            ValueError: If no CSV files found
        """
        input_folder = self.csv_config.input_folder

        if not input_folder.exists():
            raise FileNotFoundError(f"Input folder not found: {input_folder}")

        if self.file_config.mode == 'all':
            # Get all CSV files in the folder
            csv_files = list(input_folder.glob("*.csv"))
        else:
            # Get only selected files
            csv_files = [
                input_folder / filename
                for filename in self.file_config.selected_files
                if (input_folder / filename).exists()
            ]

            # Warn about missing files
            missing_files = [
                filename for filename in self.file_config.selected_files
                if not (input_folder / filename).exists()
            ]
            if missing_files:
                self.logger.warning(f"Selected files not found: {missing_files}")

        if not csv_files:
            raise ValueError(f"No CSV files found in {input_folder}")

        self.logger.info(f"Found {len(csv_files)} CSV file(s) to process")
        return sorted(csv_files)

    def read_csv_with_metadata_removal(self, file_path: Path) -> pd.DataFrame:
        """
        Read CSV file and remove metadata rows from header and footer.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame with metadata removed

        Raises:
            pd.errors.ParserError: If CSV parsing fails
        """
        skip_header = self.csv_config.skip_header_rows
        skip_footer = self.csv_config.skip_footer_rows

        self.logger.debug(
            f"Reading {file_path.name} (skip_header={skip_header}, skip_footer={skip_footer})"
        )

        try:
            # Read CSV with header skipping
            df = pd.read_csv(
                file_path,
                skiprows=skip_header,
                skipfooter=skip_footer,
                encoding=self.csv_config.encoding,
                delimiter=self.csv_config.delimiter,
                engine='python' if skip_footer > 0 else 'c',  # python engine supports skipfooter
                low_memory=False
            )

            self.logger.info(
                f"Read {file_path.name}: {len(df)} rows, {len(df.columns)} columns"
            )

            return df

        except Exception as e:
            self.logger.error(f"Error reading {file_path.name}: {e}")
            raise

    def get_table_name(self, csv_filename: str) -> str:
        """
        Determine table name based on CSV filename and configuration.

        Args:
            csv_filename: Name of the CSV file

        Returns:
            Table name to use (sanitized if enabled)
        """
        if self.table_config.table_naming == 'custom':
            # Use custom mapping if available
            table_name = self.table_config.custom_table_names.get(
                csv_filename,
                Path(csv_filename).stem  # Fallback to filename without extension
            )
        else:
            # Use filename without extension
            table_name = Path(csv_filename).stem

        # Apply sanitization if enabled
        if self.table_config.enable_sanitization:
            original_name = table_name
            table_name = self.sanitizer.sanitize(csv_filename)

            # Log if name was changed
            if original_name != table_name:
                self.logger.info(f"Sanitized table name: '{original_name}' → '{table_name}'")

        # Apply table prefix if configured
        if self.table_config.table_prefix:
            # Sanitize the prefix to ensure SQL Server compliance
            sanitized_prefix = self._sanitize_prefix(self.table_config.table_prefix)

            if sanitized_prefix:
                original_table_name = table_name

                # Calculate max base name length to stay within SQL Server's 128 char limit
                max_base_length = 128 - len(sanitized_prefix)

                # Truncate base name if necessary to preserve full prefix
                if len(table_name) > max_base_length:
                    self.logger.warning(
                        f"Table name '{table_name}' is too long with prefix '{sanitized_prefix}'. "
                        f"Truncating base name from {len(table_name)} to {max_base_length} characters."
                    )
                    table_name = table_name[:max_base_length]

                # Apply prefix
                table_name = f"{sanitized_prefix}{table_name}"

                # Log prefix application
                self.logger.info(f"Applied table prefix: '{original_table_name}' → '{table_name}'")

        # Validate the final table name (including prefix)
        if not self.sanitizer.validate_table_name(table_name):
            self.logger.warning(
                f"Table name '{table_name}' may not be valid for SQL Server"
            )

        return table_name

    def load_dataframe_to_sql(
        self,
        df: pd.DataFrame,
        table_name: str,
        csv_filename: str
    ) -> None:
        """
        Load DataFrame into SQL Server table.

        Args:
            df: DataFrame to load
            table_name: Target table name
            csv_filename: Original CSV filename (for dtype overrides)

        Raises:
            SQLAlchemyError: If loading fails
        """
        try:
            # Get dtype overrides for this table
            dtype = None
            if csv_filename in self.table_config.dtype_overrides:
                dtype = self.table_config.dtype_overrides[csv_filename]
                self.logger.debug(f"Applying dtype overrides: {dtype}")

            # Load data to SQL
            chunk_size = self.csv_config.chunk_size

            self.logger.info(
                f"Loading {len(df)} rows into [{self.table_config.schema}].[{table_name}] "
                f"(mode: {self.table_config.if_exists})"
            )

            df.to_sql(
                name=table_name,
                con=self.engine,
                schema=self.table_config.schema,
                if_exists=self.table_config.if_exists,
                index=False,
                chunksize=chunk_size,
                dtype=dtype,
                method='multi'  # Use multi-row INSERT for better performance
            )

            self.logger.info(f"Successfully loaded data into {table_name}")

        except SQLAlchemyError as e:
            self.logger.error(f"Error loading data into {table_name}: {e}")
            raise

    def create_indexes(self, table_name: str) -> None:
        """
        Create indexes on specified columns for a table.

        Supports both prefixed and base table names in configuration.
        First tries to find index config by the full table name (with prefix),
        then falls back to base name (without prefix) for backward compatibility.

        Args:
            table_name: Final table name (already includes prefix if configured)
        """
        # Try to find index config by full name first
        columns = None

        if table_name in self.table_config.create_indexes:
            columns = self.table_config.create_indexes[table_name]
        # If not found and we have a prefix, try looking up by base name
        elif self.table_config.table_prefix:
            sanitized_prefix = self._sanitize_prefix(self.table_config.table_prefix)
            if sanitized_prefix and table_name.startswith(sanitized_prefix):
                # Extract base name by removing prefix
                base_name = table_name[len(sanitized_prefix):]
                if base_name in self.table_config.create_indexes:
                    columns = self.table_config.create_indexes[base_name]
                    self.logger.debug(
                        f"Found index config for base name '{base_name}' "
                        f"(full table: '{table_name}')"
                    )

        if not columns:
            return

        try:
            with self.engine.connect() as conn:
                for column in columns:
                    index_name = f"idx_{table_name}_{column}"

                    # Check if index already exists
                    check_query = text(f"""
                        SELECT COUNT(*) as cnt
                        FROM sys.indexes
                        WHERE name = :index_name
                        AND object_id = OBJECT_ID(:full_table_name)
                    """)

                    full_table_name = f"{self.table_config.schema}.{table_name}"
                    result = conn.execute(
                        check_query,
                        {"index_name": index_name, "full_table_name": full_table_name}
                    ).fetchone()

                    if result[0] > 0:
                        self.logger.debug(f"Index {index_name} already exists")
                        continue

                    # Create index
                    create_index_query = text(f"""
                        CREATE INDEX {index_name}
                        ON [{self.table_config.schema}].[{table_name}] ([{column}])
                    """)

                    conn.execute(create_index_query)
                    conn.commit()

                    self.logger.info(f"Created index {index_name} on {table_name}.{column}")

        except SQLAlchemyError as e:
            self.logger.warning(f"Error creating indexes on {table_name}: {e}")

    def process_file(self, file_path: Path) -> bool:
        """
        Process a single CSV file and load it into SQL Server.

        Args:
            file_path: Path to CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing file: {file_path.name}")

            # Read CSV with metadata removal
            df = self.read_csv_with_metadata_removal(file_path)

            if df.empty:
                self.logger.warning(f"Skipping {file_path.name}: No data after metadata removal")
                return False

            # Determine table name
            table_name = self.get_table_name(file_path.name)

            # Load to SQL Server
            self.load_dataframe_to_sql(df, table_name, file_path.name)

            # Create indexes if configured
            self.create_indexes(table_name)

            self.logger.info(f"Successfully processed {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to process {file_path.name}: {e}", exc_info=True)
            return False

    def run(self) -> Dict[str, Any]:
        """
        Main execution method to process all CSV files.

        Returns:
            Dictionary with execution results and statistics
        """
        self.logger.info("=" * 70)
        self.logger.info("CSV to MS SQL Server Loader - Starting")
        self.logger.info("=" * 70)

        results = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'processed_files': [],
            'failed_files': []
        }

        try:
            # Connect to database
            self.connect_database()

            # Get list of files to process
            csv_files = self.get_csv_files()
            results['total_files'] = len(csv_files)

            # Process each file
            for file_path in csv_files:
                success = self.process_file(file_path)

                if success:
                    results['successful'] += 1
                    results['processed_files'].append(file_path.name)
                else:
                    results['failed'] += 1
                    results['failed_files'].append(file_path.name)

            # Summary
            self.logger.info("=" * 70)
            self.logger.info("Processing Complete")
            self.logger.info(f"Total files: {results['total_files']}")
            self.logger.info(f"Successful: {results['successful']}")
            self.logger.info(f"Failed: {results['failed']}")
            self.logger.info("=" * 70)

            return results

        except Exception as e:
            self.logger.error(f"Fatal error during execution: {e}", exc_info=True)
            raise

        finally:
            if self.engine:
                self.engine.dispose()
                self.logger.info("Database connection closed")


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Load CSV files into Microsoft SQL Server with metadata removal',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default config.yaml
  python load_csv_to_mssql.py

  # Use custom config file
  python load_csv_to_mssql.py --config my_config.yaml

  # Show version
  python load_csv_to_mssql.py --version
        """
    )

    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='CSV to MSSQL Loader v1.0.0'
    )

    args = parser.parse_args()

    try:
        # Create and run loader
        loader = CSVToMSSQLLoader(config_path=args.config)
        results = loader.run()

        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)

    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
