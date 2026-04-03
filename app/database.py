import sqlite3
from typing import Any


def init_db() -> sqlite3.Connection:
    """
    Create in-memory SQLite database, initialize schema and sample data.
    Returns connection object.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    cursor = conn.cursor()
    
    # Create schema
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL,
            manager_id INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            location TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    
    # Insert sample data - employees
    cursor.execute("""
        INSERT INTO employees VALUES
        (1, 'Alice', 'Engineering', 95000, '2020-01-15', NULL),
        (2, 'Bob', 'Engineering', 85000, '2021-03-10', 1),
        (3, 'Carol', 'Marketing', 70000, '2019-07-22', NULL),
        (4, 'David', 'Marketing', 65000, '2022-05-01', 3),
        (5, 'Eve', 'HR', 60000, '2020-11-30', NULL),
        (6, 'Frank', 'Engineering', 90000, '2018-09-14', 1),
        (7, 'Grace', 'HR', 55000, '2023-02-28', 5),
        (8, 'Henry', 'Marketing', 72000, '2021-08-19', 3)
    """)
    
    # Insert sample data - departments
    cursor.execute("""
        INSERT INTO departments VALUES
        (1, 'Engineering', 500000, 'New York'),
        (2, 'Marketing', 300000, 'Chicago'),
        (3, 'HR', 150000, 'Austin'),
        (4, 'Finance', 200000, 'New York')
    """)
    
    # Insert sample data - orders
    cursor.execute("""
        INSERT INTO orders VALUES
        (1, 'Acme Corp', 'Laptop', 1200.00, '2024-01-10', 'completed'),
        (2, 'Beta LLC', 'Monitor', 450.00, '2024-01-15', 'pending'),
        (3, 'Acme Corp', 'Keyboard', 80.00, '2024-01-20', 'completed'),
        (4, 'Gamma Inc', 'Laptop', 1200.00, '2024-02-01', 'cancelled'),
        (5, 'Delta Co', 'Mouse', 40.00, '2024-02-10', 'completed'),
        (6, 'Beta LLC', 'Laptop', 1200.00, '2024-02-15', 'pending'),
        (7, 'Acme Corp', 'Monitor', 450.00, '2024-03-01', 'completed'),
        (8, 'Epsilon Ltd', 'Keyboard', 80.00, '2024-03-05', 'pending')
    """)
    
    # Insert sample data - products
    cursor.execute("""
        INSERT INTO products VALUES
        (1, 'Laptop', 'Electronics', 1200.00, 15),
        (2, 'Monitor', 'Electronics', 450.00, 30),
        (3, 'Keyboard', 'Accessories', 80.00, 100),
        (4, 'Mouse', 'Accessories', 40.00, 150),
        (5, 'Desk', 'Furniture', 350.00, 20),
        (6, 'Chair', 'Furniture', 250.00, 25)
    """)
    
    conn.commit()
    return conn


def execute_query(conn: sqlite3.Connection, query: str) -> tuple[list[dict], str | None]:
    """
    Execute a SQL query against the database.
    
    Returns:
        (result_rows_as_list_of_dicts, error_message_or_None)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Fetch results if it's a SELECT query
        if query.strip().upper().startswith('SELECT') or query.strip().upper().startswith('WITH'):
            rows = cursor.fetchall()
            # Convert Row objects to dictionaries
            result = [dict(row) for row in rows]
            return result, None
        else:
            # For non-SELECT queries (shouldn't happen in this env, but handle gracefully)
            conn.commit()
            return [], None
            
    except sqlite3.Error as e:
        error_message = f"sqlite3.{type(e).__name__}: {str(e)}"
        return [], error_message
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        return [], error_message


def compare_results(actual: list[dict], expected: list[dict]) -> float:
    """
    Compare actual query result to expected result.
    
    Returns a float 0.0–1.0:
      1.0 → exact match (same rows, same values, order ignored)
      0.5 → same columns, partially matching rows
      0.0 → completely wrong or empty when expected non-empty
    """
    # If both empty, that's a match
    if len(actual) == 0 and len(expected) == 0:
        return 1.0
    
    # If one is empty and the other isn't, that's wrong
    if len(actual) == 0 or len(expected) == 0:
        return 0.0
    
    # Check if columns match
    actual_cols = set(actual[0].keys()) if actual else set()
    expected_cols = set(expected[0].keys()) if expected else set()
    
    if actual_cols != expected_cols:
        # Different columns = wrong structure
        return 0.0
    
    # Sort both lists by converting to tuples for comparison
    # This makes order-independent comparison
    def row_to_tuple(row: dict) -> tuple:
        # Sort by keys to ensure consistent ordering
        # Convert None to a special value for sorting
        return tuple((k, row[k] if row[k] is not None else '__NULL__') for k in sorted(row.keys()))
    
    try:
        actual_sorted = sorted([row_to_tuple(row) for row in actual])
        expected_sorted = sorted([row_to_tuple(row) for row in expected])
        
        # Exact match
        if actual_sorted == expected_sorted:
            return 1.0
        
        # Partial match - count how many rows match
        actual_set = set(actual_sorted)
        expected_set = set(expected_sorted)
        
        matching_rows = len(actual_set.intersection(expected_set))
        total_expected_rows = len(expected_set)
        
        if matching_rows == 0:
            return 0.0
        
        # Partial credit: at least some rows match
        match_ratio = matching_rows / total_expected_rows
        
        # Return 0.5 if partially correct (same structure, some matches)
        if match_ratio > 0:
            return 0.5
        
        return 0.0
    except Exception as e:
        # If comparison fails, log and return 0
        print(f"Error comparing results: {e}")
        return 0.0


def get_schema_description() -> str:
    """
    Returns a human-readable description of the database schema.
    """
    return """
Database Schema:

Table: employees
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT)
  - department (TEXT)
  - salary (REAL)
  - hire_date (TEXT, format: YYYY-MM-DD)
  - manager_id (INTEGER, foreign key to employees.id)

Table: departments
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT)
  - budget (REAL)
  - location (TEXT)

Table: orders
  - id (INTEGER, PRIMARY KEY)
  - customer_name (TEXT)
  - product (TEXT)
  - amount (REAL)
  - order_date (TEXT, format: YYYY-MM-DD)
  - status (TEXT: 'completed', 'pending', 'cancelled')

Table: products
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT)
  - category (TEXT)
  - price (REAL)
  - stock (INTEGER)
""".strip()
