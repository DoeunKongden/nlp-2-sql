import sqlalchemy
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def get_database_schema(engine):
    """
    Retrieve the schema (Tables and Column) of the connected database.
    """
    inspector = sqlalchemy.inspect(engine)
    schema = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col["name"] for col in columns]

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


def create_readonly_user(engine, database_name):
    try:
        readonly_username = "llm_readonly_user"
        readonly_password = "llm_readonly_password"  # You can generate a secure password here

        # Use raw_connection for administrative commands
        connection = engine.raw_connection()
        cursor = connection.cursor()

        try:
            # Check if the user already exists
            cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{readonly_username}';")
            user_exists = cursor.fetchone()

            if user_exists:
                logger.info(f"Read-only user '{readonly_username}' already exists, skipping creation.")
            else:
                # Create a read-only user
                cursor.execute(f"CREATE USER {readonly_username} WITH PASSWORD '{readonly_password}';")
                cursor.execute(f"GRANT CONNECT ON DATABASE {database_name} TO {readonly_username};")

                # Grant read-only access to all tables in the public schema
                cursor.execute(f"GRANT USAGE ON SCHEMA public TO {readonly_username};")
                cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {readonly_username};")

                # Ensure future tables are also granted read-only access
                cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {readonly_username};")

                # Commit the transaction to apply changes
                connection.commit()

                logger.info(f"Read-only user '{readonly_username}' created successfully.")

        except Exception as e:
            connection.rollback()  # Rollback if any error occurs
            logger.error(f"Failed to create read-only user: {str(e)}")
        finally:
            # Clean up cursor and connection
            cursor.close()
            connection.close()

    except Exception as e:
        logger.error(f"Error while handling connection: {str(e)}")
