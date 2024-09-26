from app.db.connections import get_database_connection
from app.services.query_chain import generate_sql_and_execute, generate_plot_code_from_ai
from app.services.query_service import generate_sql_from_question, execute_sql
from app.services.visualization_service import execute_plot_code, visualize_data
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from io import BytesIO
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
        return {"message": "Database connected successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-sql-chain/")
async def ask_question_chain(question: str, engine=Depends(get_engine)):
    try:
        sql_query_result = generate_sql_and_execute(question, engine)
        return {"result": sql_query_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-to-visualization")
async def data_to_visualization(question: str, engine=Depends(get_engine)):
    try:
        # Generate SQL and Execute
        sql_result = generate_sql_and_execute(question, engine)

        if not sql_result or not sql_result['result']:
            raise HTTPException(status_code=500, detail="No data return from SQL query.")

        # Generate the visualization
        buf = visualize_data(sql_result['result'])

        # return the plot as an image (png)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=(str(e)))


@router.post("/code-to-visualization")
async def code_to_visualization(question: str, engine=Depends(get_engine)):
    try:
        # Generate SQL query from the question
        sql_result = generate_sql_and_execute(question, engine)

        if not sql_result:
            return {"error": "No data found for the query."}

        # Generate Python Code for the visualization
        plot_code = generate_plot_code_from_ai(sql_result, question)

        if not plot_code:
            return {"error": "Failed to generate python code for visualization."}
        plot_image = visualize_data(sql_result['result'])

        # Execute the python plot code and return the image
        buf = execute_plot_code(plot_code, sql_result['result'])
        if buf:
            return StreamingResponse(buf, media_type="image/png")
        else:
            return {"error": "Failed to generate the plot "}

    except Exception as e:
        raise HTTPException(status_code=500, detail=(str(e)))

# @router.post("/ask/")
# async def ask_question(question: str, db_type: str, engine=Depends(get_engine)):
#     try:
#         sql_query = generate_sql_from_question(db_type, question)
#         results = execute_sql(engine, sql_query)
#         plain_language_response = get_ai_response(db_type, question)
#
#         return {
#             "sql_query": sql_query,
#             "result": results,
#             "plain_language_response": plain_language_response.content
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/code-2-visualize")
# async def ask_and_visualize(question: str, db_type: str, engine=Depends(get_engine)):
#     try:
#         # step 1 : AI generate SQL Queries
#         sql_query = generate_sql_from_question(db_type, question)
#
#         # Step 2 : Execute the SQL Queries to get result
#         results = execute_sql(engine, sql_query)
#
#         # Step 3 : Generate python code for plotting the visualization
#         plot_code = get_ai_plot_code(db_type, question, results)
#
#         # Step 4 : Execute The AI generate plot code
#         buf = execute_plot_code(plot_code, results)
#
#         return StreamingResponse(buf, media_type="image/png")
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/data-2-visualize/")
# async def data_2_visualize(question: str, db_type: str, engine=Depends(get_engine)):
#     try:
#         # Generate the SQL from question using AI
#         sql_query = generate_sql_from_question(db_type, question)
#
#         # Execute the SQL queries
#         results = execute_sql(engine, sql_query)
#
#         # Visualize the data, base on query result
#         plot_image = visualize_data(results)
#
#         # Ensure the plot image is binary system(BytesIO)
#         if not isinstance(plot_image, BytesIO):
#             raise HTTPException(status_code=500, detail="Error generating the plot.")
#
#         # Return the plot as a PNG image via StreamingResponse
#         return StreamingResponse(plot_image, media_type="image/png")
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
