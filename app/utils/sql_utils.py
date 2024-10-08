import sqlalchemy
from decimal import Decimal


def get_database_schema(engine):
    """
    Retrieve the schema (Tables and Column) of the connected database.
    """
    inspector = sqlalchemy.inspect(engine)
    schema = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col['name'] for col in columns]

    return schema


def convert_decimal_to_float(result):
    """
    Converts all Decimal values in the result to float.
    Args:
        result (list): The SQL result as a list of dictionaries.

    Returns:
        list: The result with Decimal values converted to float.
    """
    for row in result:
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = float(value)
    return result
