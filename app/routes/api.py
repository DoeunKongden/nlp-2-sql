from app.db.connections import get_database_connection
from app.services.query_chain import generate_sql_and_execute, generate_plot_code_from_ai
from app.services.visualization_service import execute_plot_code, visualize_data
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text

router = APIRouter()

# Global variable to store the async engine
db_engine: AsyncEngine = None


# Dependency to get the engine (or session)
async def get_engine():
    global db_engine
    if db_engine is None:
        raise HTTPException(status_code=500, detail="No database connection established. Please connect first.")
    return db_engine


@router.post("/connect_db")
async def connect_db(db_type: str, user: str, password: str, host: str, database: str):
    global db_engine
    try:
        # Initialize the engine once using the connection parameters
        db_engine = await get_database_connection(db_type, user, password, host, database)

        # Test the connection by running a basic query
        async with AsyncSession(db_engine) as session:
            await session.execute(text("SELECT 1"))  # Basic check if DB is reachable

        return {"message": "Database connected successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-query/")
async def test_query(engine=Depends(get_engine)):
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            rows = await result.fetchall()
            return {"result": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-sql-chain/")
async def ask_question_chain(question: str, engine=Depends(get_engine)):
    try:
        # Obtain an async connection from the engine
        async with engine.connect() as conn:
            print(f"Type of connection : {type(conn)}")
            sql_query_result = await generate_sql_and_execute(question, conn)  # Ensure async
            return {"result": sql_query_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-to-visualization")
async def data_to_visualization(question: str):
    try:
        # Generate SQL and Execute
        sql_result = await generate_sql_and_execute(question, db_engine)

        if not sql_result or not sql_result['result']:
            raise HTTPException(status_code=500, detail="No data returned from SQL query.")

        # Generate the visualization
        buf = await visualize_data(sql_result['result'])  # Ensure async

        # Return the plot as an image (png)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=(str(e)))


@router.post("/code-to-visualization")
async def code_to_visualization(question: str):
    try:
        # Generate SQL query from the question
        sql_result = await generate_sql_and_execute(question, db_engine)

        if not sql_result:
            return {"error": "No data found for the query."}

        # Generate Python Code for the visualization
        plot_code = await generate_plot_code_from_ai(sql_result, question)

        if not plot_code:
            return {"error": "Failed to generate python code for visualization."}

        # Execute the python plot code and return the image
        buf = await execute_plot_code(plot_code, sql_result['result'])

        if buf:
            return StreamingResponse(buf, media_type="image/png")
        else:
            return {"error": "Failed to generate the plot."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=(str(e)))
