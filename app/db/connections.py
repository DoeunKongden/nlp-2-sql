from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool


def get_database_connection(db_type, user, password, host, database):
    try:
        if db_type == "postgresql":
            connection_string = f'postgresql+psycopg2://{user}:{password}@{host}/{database}'
        elif db_type == "mysql":
            connection_string = f'mysql+mysqlconnector://{user}:{password}@{host}/{database}'
        else:
            raise ValueError("Unsupported Database Type.")

        # Create an engine with connection pooling (NullPool is used for no pooling, but can be customized)
        engine = create_engine(connection_string, pool_pre_ping=True, pool_size=5, max_overflow=10)

        return engine

    except SQLAlchemyError as e:
        print(f"Error connecting to the database: {str(e)}")
        return None
