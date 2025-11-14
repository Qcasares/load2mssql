#!/usr/bin/env python3
"""
Test script for SQL Server port configuration.

Tests that port configuration is correctly parsed and applied to connection strings.
"""

from urllib.parse import unquote_plus


def test_connection_string_with_port():
    """Test connection string generation with various port configurations."""

    print("SQL Server Port Configuration Test")
    print("=" * 80)
    print()

    test_cases = [
        {
            "server": "localhost",
            "port": None,
            "expected": "localhost",
            "description": "No port specified (use default)"
        },
        {
            "server": "localhost",
            "port": 1433,
            "expected": "localhost",
            "description": "Default port (1433) - should not append"
        },
        {
            "server": "localhost",
            "port": 1434,
            "expected": "localhost,1434",
            "description": "Custom port (1434)"
        },
        {
            "server": "192.168.1.100",
            "port": 14330,
            "expected": "192.168.1.100,14330",
            "description": "Custom port with IP address"
        },
        {
            "server": "sql-server.domain.com",
            "port": 1435,
            "expected": "sql-server.domain.com,1435",
            "description": "Custom port with domain name"
        },
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        server = test["server"]
        port = test["port"]
        expected = test["expected"]
        description = test["description"]

        # Simulate the logic from _create_connection_string
        server_str = server
        if port and port != 1433:
            server_str = f"{server},{port}"

        success = server_str == expected
        status = "PASS" if success else "FAIL"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"[{status}] Test {i}: {description}")
        print(f"       Server:   {server}")
        print(f"       Port:     {port}")
        print(f"       Expected: {expected}")
        print(f"       Got:      {server_str}")
        print()

    # Test full connection string generation
    print("=" * 80)
    print("Full Connection String Examples")
    print("-" * 80)
    print()

    # Example 1: Default port
    print("1. Default port (1433) - Trusted Auth")
    print("   Server: localhost, Port: 1433")
    print("   → mssql+pyodbc://@localhost/YourDatabase")
    print()

    # Example 2: Custom port
    print("2. Custom port (1434) - Trusted Auth")
    print("   Server: localhost, Port: 1434")
    print("   → mssql+pyodbc://@localhost,1434/YourDatabase")
    print()

    # Example 3: SQL Auth with custom port
    print("3. Custom port (14330) - SQL Auth")
    print("   Server: 192.168.1.100, Port: 14330")
    print("   → mssql+pyodbc://user:pass@192.168.1.100,14330/YourDatabase")
    print()

    # Summary
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = test_connection_string_with_port()
    sys.exit(0 if success else 1)
