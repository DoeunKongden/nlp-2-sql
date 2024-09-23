from sqlalchemy import create_engine

def get_database_connection(db_type,user,password,host,database):
    
    if db_type == "postgresql":
        connection_string =  f'postgresql+psycopg2://{user}:{password}@{host}/{database}'
    elif db_type == "mysql":
        connection_string = f'mysql+mysqlconnector://{user}:{password}@{host}/{database}'
    else:
        raise ValueError("Unsupported Database Type.")
    
    engine = create_engine(connection_string)
    
    return engine