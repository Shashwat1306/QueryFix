"""
Task 3: Hard
Fix complex multi-layer bugs — wrong CTEs, nested subquery logic errors,
self-join issues, and queries that run but return subtly wrong results.
"""

TASK_INFO = {
    "task_id": "hard",
    "description": "Fix complex multi-layer bugs in CTEs, self-joins, nested subqueries, and subtle logic errors",
    "difficulty": "hard",
    "num_queries": 8,
    "max_attempts_per_query": 2,
}

HARD_QUERIES = [
    {
        "query_id": 201,
        "broken_query": """
            SELECT d.name as department, 
                   COUNT(e.id) as headcount,
                   SUM(e.salary) as total_salary,
                   ROUND(SUM(e.salary) / COUNT(e.id), 2) as avg_salary,
                   ROUND(SUM(e.salary) * 100.0 / (SELECT SUM(salary) FROM employees), 2) as salary_share_pct
            FROM departments d
            LEFT JOIN employees e ON e.department = d.name
            GROUP BY d.name
            ORDER BY total_salary DESC
        """,
        "bug_type": "null_aggregation",
        "bug_description": "Finance department has no employees. LEFT JOIN produces NULL for e.id and e.salary. COUNT(e.id) correctly returns 0 for Finance, but SUM(e.salary) returns NULL instead of 0, and the salary_share_pct calculation also returns NULL. Must wrap SUM with COALESCE to handle NULLs from the LEFT JOIN.",
        "correct_query": """
            SELECT d.name as department,
                   COUNT(e.id) as headcount,
                   COALESCE(SUM(e.salary), 0) as total_salary,
                   CASE WHEN COUNT(e.id) = 0 THEN 0 
                        ELSE ROUND(SUM(e.salary) / COUNT(e.id), 2) END as avg_salary,
                   ROUND(COALESCE(SUM(e.salary), 0) * 100.0 / (SELECT SUM(salary) FROM employees), 2) as salary_share_pct
            FROM departments d
            LEFT JOIN employees e ON e.department = d.name
            GROUP BY d.name
            ORDER BY total_salary DESC
        """,
        "expected_result": [
            {"department": "Engineering", "headcount": 3, "total_salary": 270000, "avg_salary": 90000.0, "salary_share_pct": 45.61},
            {"department": "Marketing", "headcount": 3, "total_salary": 207000, "avg_salary": 69000.0, "salary_share_pct": 34.97},
            {"department": "HR", "headcount": 2, "total_salary": 115000, "avg_salary": 57500.0, "salary_share_pct": 19.43},
            {"department": "Finance", "headcount": 0, "total_salary": 0, "avg_salary": 0, "salary_share_pct": 0.0},
        ],
        "error_message": "No error but some department rows have unexpected NULL values in numeric columns",
        "expected_output_hint": "Should return one row per department showing headcount and salary aggregations"
    },
    {
        "query_id": 202,
        "broken_query": """
            SELECT 
                customer_name,
                SUM(amount) as total_spent,
                COUNT(*) as order_count,
                SUM(amount) / COUNT(*) as avg_order_value
            FROM orders
            WHERE status = 'completed'
            GROUP BY customer_name
            HAVING total_spent = (SELECT MAX(total_spent) FROM (
                SELECT customer_name, SUM(amount) as total_spent
                FROM orders
                GROUP BY customer_name
            ))
        """,
        "bug_type": "subquery_scope",
        "bug_description": "Inner subquery in HAVING doesn't filter by status='completed', so MAX is calculated over all orders",
        "correct_query": """
            SELECT 
                customer_name,
                SUM(amount) as total_spent,
                COUNT(*) as order_count,
                SUM(amount) / COUNT(*) as avg_order_value
            FROM orders
            WHERE status = 'completed'
            GROUP BY customer_name
            HAVING total_spent = (SELECT MAX(total_spent) FROM (
                SELECT customer_name, SUM(amount) as total_spent
                FROM orders
                WHERE status = 'completed'
                GROUP BY customer_name
            ))
        """,
        "expected_result": [
            {"customer_name": "Acme Corp", "total_spent": 1730.0, "order_count": 3, "avg_order_value": 576.6666666666666},
        ],
        "error_message": "No error but returns wrong customer or no rows",
        "expected_output_hint": "Should return the top customer by completed order spend only"
    },
    {
        "query_id": 203,
        "broken_query": """
            SELECT 
                e.name,
                e.salary,
                e.department,
                m.name as manager_name
            FROM employees e
            LEFT JOIN employees m ON e.id = m.manager_id
        """,
        "bug_type": "self_join",
        "bug_description": "Self-join condition is inverted. Should join e.manager_id = m.id to get each employee's manager",
        "correct_query": """
            SELECT 
                e.name,
                e.salary,
                e.department,
                m.name as manager_name
            FROM employees e
            LEFT JOIN employees m ON e.manager_id = m.id
        """,
        "expected_result": [
            {"name": "Alice", "salary": 95000, "department": "Engineering", "manager_name": None},
            {"name": "Bob", "salary": 85000, "department": "Engineering", "manager_name": "Alice"},
            {"name": "Carol", "salary": 70000, "department": "Marketing", "manager_name": None},
            {"name": "David", "salary": 65000, "department": "Marketing", "manager_name": "Carol"},
            {"name": "Eve", "salary": 60000, "department": "HR", "manager_name": None},
            {"name": "Frank", "salary": 90000, "department": "Engineering", "manager_name": "Alice"},
            {"name": "Grace", "salary": 55000, "department": "HR", "manager_name": "Eve"},
            {"name": "Henry", "salary": 72000, "department": "Marketing", "manager_name": "Carol"},
        ],
        "error_message": "No error but returns wrong manager names",
        "expected_output_hint": "Should return each employee paired with their direct manager's name"
    },
    {
        "query_id": 204,
        "broken_query": """
            SELECT 
                product,
                SUM(amount) as revenue,
                ROUND(SUM(amount) * 100.0 / (SELECT SUM(amount) FROM orders), 2) as revenue_pct
            FROM orders
            WHERE status = 'completed'
            GROUP BY product
            ORDER BY revenue DESC
        """,
        "bug_type": "percentage_calculation",
        "bug_description": "The denominator uses total revenue from ALL orders (including pending/cancelled), but numerator only counts completed",
        "correct_query": """
            SELECT 
                product,
                SUM(amount) as revenue,
                ROUND(SUM(amount) * 100.0 / (SELECT SUM(amount) FROM orders WHERE status = 'completed'), 2) as revenue_pct
            FROM orders
            WHERE status = 'completed'
            GROUP BY product
            ORDER BY revenue DESC
        """,
        "expected_result": [
            {"product": "Laptop", "revenue": 1200.0, "revenue_pct": 69.36},
            {"product": "Monitor", "revenue": 450.0, "revenue_pct": 26.01},
            {"product": "Keyboard", "revenue": 80.0, "revenue_pct": 4.62},
            {"product": "Mouse", "revenue": 40.0, "revenue_pct": 2.31},
        ],
        "error_message": "No error but percentage values are wrong",
        "expected_output_hint": "Should return revenue share % of each product among completed orders only"
    },
    {
        "query_id": 205,
        "broken_query": """
            SELECT 
                e.name,
                e.department,
                e.salary,
                manager.name as manager_name,
                manager.salary as manager_salary,
                e.salary - manager.salary as salary_diff
            FROM employees e
            JOIN employees manager ON e.manager_id = manager.id
            ORDER BY salary_diff DESC
        """,
        "bug_type": "inner_join_excludes_nulls",
        "bug_description": "INNER JOIN on manager_id excludes all employees where manager_id IS NULL (Alice, Carol, Eve — the top-level managers). The query silently returns only subordinates, missing 3 employees entirely. Should use LEFT JOIN and handle NULL manager case.",
        "correct_query": """
            SELECT 
                e.name,
                e.department,
                e.salary,
                manager.name as manager_name,
                manager.salary as manager_salary,
                CASE WHEN manager.salary IS NULL THEN NULL
                     ELSE e.salary - manager.salary END as salary_diff
            FROM employees e
            LEFT JOIN employees manager ON e.manager_id = manager.id
            ORDER BY salary_diff DESC
        """,
        "expected_result": [
            {"name": "Frank", "department": "Engineering", "salary": 90000, "manager_name": "Alice", "manager_salary": 95000, "salary_diff": -5000},
            {"name": "Bob", "department": "Engineering", "salary": 85000, "manager_name": "Alice", "manager_salary": 95000, "salary_diff": -10000},
            {"name": "Henry", "department": "Marketing", "salary": 72000, "manager_name": "Carol", "manager_salary": 70000, "salary_diff": 2000},
            {"name": "David", "department": "Marketing", "salary": 65000, "manager_name": "Carol", "manager_salary": 70000, "salary_diff": -5000},
            {"name": "Grace", "department": "HR", "salary": 55000, "manager_name": "Eve", "manager_salary": 60000, "salary_diff": -5000},
            {"name": "Alice", "department": "Engineering", "salary": 95000, "manager_name": None, "manager_salary": None, "salary_diff": None},
            {"name": "Carol", "department": "Marketing", "salary": 70000, "manager_name": None, "manager_salary": None, "salary_diff": None},
            {"name": "Eve", "department": "HR", "salary": 60000, "manager_name": None, "manager_salary": None, "salary_diff": None},
        ],
        "error_message": "No error but the result set is incomplete",
        "expected_output_hint": "Should return salary comparison between each employee and their manager"
    },
    {
        "query_id": 206,
        "broken_query": """
            SELECT 
                d.name as department,
                d.budget,
                COALESCE(SUM(e.salary), 0) as total_salary,
                d.budget - COALESCE(SUM(e.salary), 0) as budget_remaining
            FROM employees e
            RIGHT JOIN departments d ON e.department = d.name
            GROUP BY d.name, d.budget
            HAVING budget_remaining < 0
        """,
        "bug_type": "having_alias_and_logic",
        "bug_description": "Alias budget_remaining cannot be used in HAVING in SQLite",
        "correct_query": """
            SELECT 
                d.name as department,
                d.budget,
                COALESCE(SUM(e.salary), 0) as total_salary,
                d.budget - COALESCE(SUM(e.salary), 0) as budget_remaining
            FROM employees e
            RIGHT JOIN departments d ON e.department = d.name
            GROUP BY d.name, d.budget
            HAVING d.budget - COALESCE(SUM(e.salary), 0) < 0
        """,
        "expected_result": [],
        "error_message": "sqlite3.OperationalError: no such column: budget_remaining",
        "expected_output_hint": "Should return departments where total salary exceeds budget (none in this dataset, so empty result is correct)"
    },
    {
        "query_id": 207,
        "broken_query": """
            SELECT 
                o.customer_name,
                o.product,
                o.amount,
                p.price as list_price,
                o.amount - p.price as discount
            FROM orders o
            JOIN products p ON o.product = p.name
            WHERE discount > 0
            ORDER BY discount DESC
        """,
        "bug_type": "where_vs_having_computed",
        "bug_description": "Cannot reference a computed column alias (discount) in the WHERE clause. Must repeat the expression.",
        "correct_query": """
            SELECT 
                o.customer_name,
                o.product,
                o.amount,
                p.price as list_price,
                o.amount - p.price as discount
            FROM orders o
            JOIN products p ON o.product = p.name
            WHERE o.amount - p.price > 0
            ORDER BY discount DESC
        """,
        "expected_result": [],
        "error_message": "sqlite3.OperationalError: no such column: discount",
        "expected_output_hint": "Should return orders where customer paid MORE than list price (none exist in this dataset, so empty result is correct)"
    },
    {
        "query_id": 208,
        "broken_query": """
            SELECT 
                e1.department,
                e1.name as employee,
                e1.salary,
                COUNT(e2.id) + 1 as salary_rank
            FROM employees e1
            LEFT JOIN employees e2 
                ON e1.department = e2.department 
                AND e2.salary > e1.salary
            GROUP BY e1.department, e1.name, e1.salary
            ORDER BY e1.department, salary_rank DESC
        """,
        "bug_type": "ranking_logic",
        "bug_description": "Rank ordering is inverted. Should ORDER BY salary_rank ASC for correct ranking (rank 1 = highest)",
        "correct_query": """
            SELECT 
                e1.department,
                e1.name as employee,
                e1.salary,
                COUNT(e2.id) + 1 as salary_rank
            FROM employees e1
            LEFT JOIN employees e2 
                ON e1.department = e2.department 
                AND e2.salary > e1.salary
            GROUP BY e1.department, e1.name, e1.salary
            ORDER BY e1.department, salary_rank ASC
        """,
        "expected_result": [
            {"department": "Engineering", "employee": "Alice", "salary": 95000, "salary_rank": 1},
            {"department": "Engineering", "employee": "Frank", "salary": 90000, "salary_rank": 2},
            {"department": "Engineering", "employee": "Bob", "salary": 85000, "salary_rank": 3},
            {"department": "HR", "employee": "Eve", "salary": 60000, "salary_rank": 1},
            {"department": "HR", "employee": "Grace", "salary": 55000, "salary_rank": 2},
            {"department": "Marketing", "employee": "Henry", "salary": 72000, "salary_rank": 1},
            {"department": "Marketing", "employee": "Carol", "salary": 70000, "salary_rank": 2},
            {"department": "Marketing", "employee": "David", "salary": 65000, "salary_rank": 3},
        ],
        "error_message": "No error but salary rank order is inverted",
        "expected_output_hint": "Should return employees ranked 1 (highest) to N (lowest) within each department"
    },
]
