from sqlalchemy import text
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
from langchain_core.prompts import PromptTemplate
from langchain.chains.sql_database.query import create_sql_query_chain
from app.utils.sql_extraction import extract_sql_query

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

groq_llm = ChatGroq(
    model="llama3-groq-8b-8192-tool-use-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# Defining prompt template: For connecting to database and generate SQL Queries
prompt_template = """
You are connected to a {db_type} database. When the user asks a question, respond clearly in plain English first, explaining what the SQL query will do. 
Then generate a standard SQL query (without using specific database commands like `\dt`), which retrieves the answer from the database.
Question: {question}
"""

prompt = PromptTemplate.from_template(prompt_template)


def get_ai_response(db_type, question):
    # Format the prompt with the context
    prompt_with_context = prompt.format(db_type=db_type, question=question)
    try:
        # Invoke the Groq LLM by passing the prompt as a string, not a dictionary
        ai_response = groq_llm.invoke(prompt_with_context)  # Pass prompt_with_context as a string

        return ai_response

    except Exception as e:
        print(f"Error invoking LLM: {str(e)}")
        return None  # Return None in case of an error, so it's not passed to SQL execution


# function that will generate the SQL queries
def generate_sql_from_question(db_type, question):
    # Format the prompt with the context
    prompt_with_context = prompt.format(db_type=db_type, question=question)

    try:
        # Invoke the Groq LLM by passing the prompt as a string, not a dictionary
        ai_response = groq_llm.invoke(prompt_with_context)  # Pass prompt_with_context as a string

        # Extract the SQL query from the response content
        sql_response = extract_sql_query(ai_response.content)

        print("SQL response:", sql_response)
        return sql_response

    except Exception as e:
        print(f"Error invoking LLM: {str(e)}")
        return None  # Return None in case of an error, so it's not passed to SQL execution


# function that will execute the generated SQL query from the AI
def execute_sql(engine, query):
    if query is None:
        print("No valid SQL query to execute.")
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()

            # Fetch the column names
            columns = result.keys()

            # Convert the result rows into a list of dictionaries
            row_dicts = [dict(zip(columns, row)) for row in rows]
            return row_dicts
    except Exception as e:
        print(f"Error executing SQL: {str(e)}")
        return None
