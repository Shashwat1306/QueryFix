"""
Task 1: Easy
Fix syntax errors and simple clause mistakes in basic SELECT queries.
"""

TASK_INFO = {
    "task_id": "easy",
    "description": "Fix syntax errors and simple clause mistakes in basic SELECT queries",
    "difficulty": "easy",
    "num_queries": 5,
    "max_attempts_per_query": 3,
}

EASY_QUERIES = [
    {
        "query_id": 1,
        "broken_query": "SELECT name salary FROM employees",
        "bug_type": "syntax",
        "bug_description": "Missing comma between column names",
        "correct_query": "SELECT name, salary FROM employees",
        "expected_result": [
            {"name": "Alice", "salary": 95000},
            {"name": "Bob", "salary": 85000},
            {"name": "Carol", "salary": 70000},
            {"name": "David", "salary": 65000},
            {"name": "Eve", "salary": 60000},
            {"name": "Frank", "salary": 90000},
            {"name": "Grace", "salary": 55000},
            {"name": "Henry", "salary": 72000},
        ],
        "error_message": "sqlite3.OperationalError: near 'salary': syntax error",
        "expected_output_hint": "Should return all 8 employees with their name and salary"
    },
    {
        "query_id": 2,
        "broken_query": "SELECT * FORM employees WHERE department = 'Engineering'",
        "bug_type": "syntax",
        "bug_description": "Typo: FORM instead of FROM",
        "correct_query": "SELECT * FROM employees WHERE department = 'Engineering'",
        "expected_result": [
            {"id": 1, "name": "Alice", "department": "Engineering", "salary": 95000, "hire_date": "2020-01-15", "manager_id": None},
            {"id": 2, "name": "Bob", "department": "Engineering", "salary": 85000, "hire_date": "2021-03-10", "manager_id": 1},
            {"id": 6, "name": "Frank", "department": "Engineering", "salary": 90000, "hire_date": "2018-09-14", "manager_id": 1},
        ],
        "error_message": "sqlite3.OperationalError: near 'FORM': syntax error",
        "expected_output_hint": "Should return 3 Engineering employees"
    },
    {
        "query_id": 3,
        "broken_query": "SELECT department, COUNT(*) FROM employees",
        "bug_type": "clause",
        "bug_description": "Missing GROUP BY clause for aggregate query",
        "correct_query": "SELECT department, COUNT(*) as count FROM employees GROUP BY department",
        "expected_result": [
            {"department": "Engineering", "count": 3},
            {"department": "HR", "count": 2},
            {"department": "Marketing", "count": 3},
        ],
        "error_message": "No error but returns only 1 row instead of per-department counts",
        "expected_output_hint": "Should return one row per department with employee count"
    },
    {
        "query_id": 4,
        "broken_query": "SELECT * FROM orders WHERE status = completed",
        "bug_type": "syntax",
        "bug_description": "String value 'completed' missing quotes",
        "correct_query": "SELECT * FROM orders WHERE status = 'completed'",
        "expected_result": [
            {"id": 1, "customer_name": "Acme Corp", "product": "Laptop", "amount": 1200.00, "order_date": "2024-01-10", "status": "completed"},
            {"id": 3, "customer_name": "Acme Corp", "product": "Keyboard", "amount": 80.00, "order_date": "2024-01-20", "status": "completed"},
            {"id": 5, "customer_name": "Delta Co", "product": "Mouse", "amount": 40.00, "order_date": "2024-02-10", "status": "completed"},
            {"id": 7, "customer_name": "Acme Corp", "product": "Monitor", "amount": 450.00, "order_date": "2024-03-01", "status": "completed"},
        ],
        "error_message": "sqlite3.OperationalError: no such column: completed",
        "expected_output_hint": "Should return 4 completed orders"
    },
    {
        "query_id": 5,
        "broken_query": "SELECT name, salary FROM employees ORDER BY salary LIMIT 3",
        "bug_type": "logic",
        "bug_description": "Missing DESC — returns 3 lowest salaries instead of 3 highest",
        "correct_query": "SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 3",
        "expected_result": [
            {"name": "Alice", "salary": 95000},
            {"name": "Frank", "salary": 90000},
            {"name": "Bob", "salary": 85000},
        ],
        "error_message": "No error but returns wrong rows",
        "expected_output_hint": "Should return top 3 highest-paid employees"
    },
]
