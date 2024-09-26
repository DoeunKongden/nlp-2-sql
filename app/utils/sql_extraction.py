import re


def extract_sql_query(response_text: str) -> str:
    """
    Extract the SQL query from the AI's response text.
    """
    try:
        # Use regex to extract the SQL query from the response
        sql_query_match = re.search(r"SQLQuery: (.*)", response_text, re.DOTALL)

        if sql_query_match:
            # Extract the SQL query, remove unnecessary backslashes, and clean it up
            sql_query = sql_query_match.group(1).strip()
            sql_query = sql_query.replace("\\", "")  # Remove backslashes

            # Ensure the SQL query ends with a semicolon
            if not sql_query.endswith(";"):
                sql_query += ";"

            return sql_query
        else:
            raise ValueError("No valid SQL query found in the response.")
    except Exception as e:
        print(f"Error extracting SQL from response: {str(e)}")
        return None
