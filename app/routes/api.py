from app.db.connections import get_database_connection
from app.services.query_service import generate_sql_from_question,execute_sql
from fastapi import Depends, APIRouter
from fastapi import HTTPException

router = APIRouter()


def get_engine():
    return engineGlobal 

@router.post("/connect_db")
async def connect_db(db_type:str, user:str , password:str, host:str, database:str):
    try:
        global engineGlobal
        engineGlobal = get_database_connection(db_type,user,password,host,database)
        return "Success"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/ask/")
async def ask_question(question:str, db_type:str, engine = Depends(get_engine)):
    try:
        sql_query = generate_sql_from_question(db_type, question)
        results = execute_sql(engine,sql_query)
        return {"result": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))