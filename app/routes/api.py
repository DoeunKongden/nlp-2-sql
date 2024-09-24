from app.db.connections import get_database_connection
from app.services.query_service import generate_sql_from_question, execute_sql, get_ai_plot_code
from app.services.visualization_service import execute_plot_code
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.services.query_service import get_ai_response

router = APIRouter()


def get_engine():
    return engineGlobal


@router.post("/connect_db")
async def connect_db(db_type: str, user: str, password: str, host: str, database: str):
    try:
        global engineGlobal
        engineGlobal = get_database_connection(db_type, user, password, host, database)
        return "Success"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/")
async def ask_question(question: str, db_type: str, engine=Depends(get_engine)):
    try:
        sql_query = generate_sql_from_question(db_type, question)
        results = execute_sql(engine, sql_query)
        plain_language_response = get_ai_response(db_type, question)

        return {
            "sql_query": sql_query,
            "result": results,
            "plain_language_response": plain_language_response.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-to-visualize")
async def ask_and_visualize(question: str, db_type: str, engine=Depends(get_engine)):
    try:
        # step 1 : AI generate SQL Queries
        sql_query = generate_sql_from_question(db_type, question)

        # Step 2 : Execute the SQL Queries to get result
        results = execute_sql(engine, sql_query)

        # Step 3 : Generate python code for plotting the visualization
        plot_code = get_ai_plot_code(db_type, question, results)

        # Step 4 : Execute The AI generate plot code
        buf = execute_plot_code(plot_code, results)

        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
