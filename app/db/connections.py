from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine

# Declare the base class for models
Base = declarative_base()


# Function to create the database connection engine
async def get_database_connection(db_type, user, password, host, database) -> AsyncEngine:
    if db_type == "postgresql":
        connection_string = f'postgresql+asyncpg://{user}:{password}@{host}/{database}'
    elif db_type == "mysql":
        # Assuming you want to use `aiomysql` for async MySQL connections.
        connection_string = f'mysql+aiomysql://{user}:{password}@{host}/{database}'
    else:
        raise ValueError("Unsupported Database Type.")

    # Create an asynchronous engine
    async_engine = create_async_engine(connection_string, echo=True)

    return async_engine


# Create sessionmaker
def create_sessionmaker(engine: AsyncEngine):
    return sessionmaker(
        bind=engine,  # Use the async engine
        class_=AsyncSession,  # Use AsyncSession class
        autocommit=False,
        autoflush=False,
    )


# Dependency to get the database connection session
async def get_db_connection(engine: AsyncEngine):
    SessionLocal = create_sessionmaker(engine)  # Create sessionmaker with the engine
    async with SessionLocal() as session:
        yield session
