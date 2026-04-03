"""
Task 2: Medium
Fix JOIN errors, HAVING vs WHERE confusion, wrong aggregates, and subquery issues.
"""

TASK_INFO = {
    "task_id": "medium",
    "description": "Fix JOIN errors, HAVING vs WHERE confusion, wrong aggregates, and subquery issues",
    "difficulty": "medium",
    "num_queries": 7,
    "max_attempts_per_query": 3,
}

MEDIUM_QUERIES = [
    {
        "query_id": 101,
        "broken_query": """
            SELECT e.name, d.name as department_name
            FROM employees e
            INNER JOIN departments d ON e.department = d.name
            WHERE d.location = 'New York'
        """,
        "bug_type": "join",
        "bug_description": "INNER JOIN excludes employees whose department has no matching department record",
        "correct_query": """
            SELECT e.name, d.name as department_name
            FROM employees e
            LEFT JOIN departments d ON e.department = d.name
            WHERE d.location = 'New York'
        """,
        "expected_result": [
            {"name": "Alice", "department_name": "Engineering"},
            {"name": "Bob", "department_name": "Engineering"},
            {"name": "Frank", "department_name": "Engineering"},
        ],
        "error_message": "No error but returns wrong result set",
        "expected_output_hint": "Should return 3 Engineering employees based in New York"
    },
    {
        "query_id": 102,
        "broken_query": """
            SELECT department, AVG(salary) as avg_salary
            FROM employees
            WHERE AVG(salary) > 70000
            GROUP BY department
        """,
        "bug_type": "having_vs_where",
        "bug_description": "Cannot use aggregate function AVG() in WHERE clause — must use HAVING",
        "correct_query": """
            SELECT department, AVG(salary) as avg_salary
            FROM employees
            GROUP BY department
            HAVING AVG(salary) > 70000
        """,
        "expected_result": [
            {"department": "Engineering", "avg_salary": 90000.0},
            {"department": "Marketing", "avg_salary": 69000.0},
        ],
        "error_message": "sqlite3.OperationalError: misuse of aggregate function AVG()",
        "expected_output_hint": "Should return departments where average salary exceeds 70000"
    },
    {
        "query_id": 103,
        "broken_query": """
            SELECT customer_name, SUM(amount) as total
            FROM orders
            WHERE status = 'completed'
            GROUP BY customer_name
            ORDER BY total
            LIMIT 1
        """,
        "bug_type": "logic",
        "bug_description": "ORDER BY without DESC returns the lowest total, not the highest",
        "correct_query": """
            SELECT customer_name, SUM(amount) as total
            FROM orders
            WHERE status = 'completed'
            GROUP BY customer_name
            ORDER BY total DESC
            LIMIT 1
        """,
        "expected_result": [
            {"customer_name": "Acme Corp", "total": 1730.0},
        ],
        "error_message": "No error but returns wrong customer",
        "expected_output_hint": "Should return the single customer with the highest total completed order value"
    },
    {
        "query_id": 104,
        "broken_query": """
            SELECT name, salary
            FROM employees
            WHERE salary > (SELECT salary FROM employees WHERE department = 'HR')
        """,
        "bug_type": "subquery",
        "bug_description": "Subquery returns multiple rows (2 HR employees) but > operator expects exactly one value",
        "correct_query": """
            SELECT name, salary
            FROM employees
            WHERE salary > (SELECT MAX(salary) FROM employees WHERE department = 'HR')
        """,
        "expected_result": [
            {"name": "Alice", "salary": 95000},
            {"name": "Bob", "salary": 85000},
            {"name": "Carol", "salary": 70000},
            {"name": "Frank", "salary": 90000},
            {"name": "Henry", "salary": 72000},
        ],
        "error_message": "sqlite3.OperationalError: sub-select returns 2 columns",
        "expected_output_hint": "Should return all employees earning more than the highest HR salary (60000)"
    },
    {
        "query_id": 105,
        "broken_query": """
            SELECT p.name, COUNT(o.id) as order_count
            FROM products p
            INNER JOIN orders o ON p.name = o.product
            GROUP BY p.name
        """,
        "bug_type": "join",
        "bug_description": "INNER JOIN excludes products with no orders. Should use LEFT JOIN to include all products.",
        "correct_query": """
            SELECT p.name, COUNT(o.id) as order_count
            FROM products p
            LEFT JOIN orders o ON p.name = o.product
            GROUP BY p.name
        """,
        "expected_result": [
            {"name": "Chair", "order_count": 0},
            {"name": "Desk", "order_count": 0},
            {"name": "Keyboard", "order_count": 2},
            {"name": "Laptop", "order_count": 3},
            {"name": "Monitor", "order_count": 2},
            {"name": "Mouse", "order_count": 1},
        ],
        "error_message": "No error but returns only 4 products instead of all 6",
        "expected_output_hint": "Should return all 6 products including those with 0 orders"
    },
    {
        "query_id": 106,
        "broken_query": """
            SELECT department, COUNT(*) as headcount, SUM(salary) as total_salary
            FROM employees
            GROUP BY department
            HAVING headcount > 2
        """,
        "bug_type": "alias",
        "bug_description": "SQLite does not allow column aliases in HAVING clause. Must repeat the expression.",
        "correct_query": """
            SELECT department, COUNT(*) as headcount, SUM(salary) as total_salary
            FROM employees
            GROUP BY department
            HAVING COUNT(*) > 2
        """,
        "expected_result": [
            {"department": "Engineering", "headcount": 3, "total_salary": 270000},
            {"department": "Marketing", "headcount": 3, "total_salary": 207000},
        ],
        "error_message": "sqlite3.OperationalError: no such column: headcount",
        "expected_output_hint": "Should return departments with more than 2 employees"
    },
    {
        "query_id": 107,
        "broken_query": """
            SELECT DISTINCT customer_name
            FROM orders
            WHERE amount > 500 AND status != 'cancelled'
            ORDERED BY customer_name
        """,
        "bug_type": "syntax",
        "bug_description": "Typo: ORDERED BY instead of ORDER BY",
        "correct_query": """
            SELECT DISTINCT customer_name
            FROM orders
            WHERE amount > 500 AND status != 'cancelled'
            ORDER BY customer_name
        """,
        "expected_result": [
            {"customer_name": "Acme Corp"},
            {"customer_name": "Beta LLC"},
        ],
        "error_message": "sqlite3.OperationalError: near 'ORDERED': syntax error",
        "expected_output_hint": "Should return distinct customers with non-cancelled orders over 500, sorted alphabetically"
    },
]
