from app.db.connections import get_database_connection
from app.services.query_chain import generate_sql_and_execute, generate_plot_code_from_ai
from app.services.visualization_service import execute_plot_code
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import logging

from app.utils.sql_utils import convert_decimal_to_float

router = APIRouter()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set logging level to INFO or DEBUG as needed

# You can also configure logging to a file or console if needed
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_engine():
    return engineGlobal


@router.post("/connect_db")
async def connect_db(db_type: str, user: str, password: str, host: str, database: str):
    try:
        global engineGlobal
        engineGlobal = get_database_connection(db_type, user, password, host, database)
        logger.info("Database connected successfully.")
        return {"message": "Database connected successfully."}
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect to database.")


@router.post("/ask-sql-chain/")
async def ask_question_chain(question: str, engine=Depends(get_engine)):
    try:
        # step 1: log after invoking the llm
        logger.info(f"Invoking Groq LLM with question: {question}")
        sql_query_result = generate_sql_and_execute(question, engine)
        logger.info(f"LLM response: {sql_query_result['response']}")

        # step 2: log after SQL execution
        logger.info(f"Executed SQL query: {sql_query_result['sql_query']}")
        logger.info(f"SQL execution result: {sql_query_result['result']}")

        return {"result": sql_query_result}
    except Exception as e:
        logger.error(f"SQL generation and execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing SQL query.")


@router.post("/code-to-visualization")
async def code_to_visualization(question: str, engine=Depends(get_engine)):
    try:
        # Step 1: Log after invoking the LLM for SQL generation
        logger.info(f"Invoking Groq LLM for SQL generation with question: {question}")
        sql_result = generate_sql_and_execute(question, engine)

        if not sql_result or not sql_result.get('response'):
            logger.warning(f"No data found for the query: {question}")
            return {"error": "No data found for the query."}

        # Convert Decimal type float in result
        sql_result['result'] = convert_decimal_to_float(sql_result['result'])
        logger.info(f"SQL result (after converting Decimal): {sql_result['result']}")

        # Step 2: Log SQL query and execution result
        logger.info(f"Generated SQL query: {sql_result['response']}")
        logger.info(f"SQL Query result: {sql_result['result']}")

        # Step 3: Log after generating python code for visualization
        logger.info("Generating Python code for visualization.")

        # Generate Python code for the visualization from the AI
        plot_code = generate_plot_code_from_ai(sql_result['result'], question)

        if not plot_code:
            logger.error("Failed to generate python code for visualization")
            return {"error": "Failed to generate Python code for visualization."}

        logger.info(f"Generated Python plot code: {plot_code}")

        # Step 4: log after executing the generated plot code
        buf = execute_plot_code(plot_code, sql_result['result'])

        if buf:
            logger.info("Plot generated successfully")
            return StreamingResponse(buf, media_type="image/png")
        else:
            logging.error("Failed to generated the plot.")
            return {"error": "Failed to generate the plot."}

    except Exception as e:
        logger.error(f"Error in code to visualization : {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during processing.")
