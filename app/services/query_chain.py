import re
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain.sql_database import SQLDatabase
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
from sqlalchemy import text
from app.services.query_service import execute_sql
from app.utils.clean_ai_plot_code import clean_ai_plot_code

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

groq_llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


def extract_sql_from_response(response_text: str) -> str:
    """
    Extracts and cleans the SQL query from the AI's response text.
    """
    try:
        # Use regex to find the SQL query more accurately, assuming AI labels it as SQLQuery
        sql_query_match = re.search(r"SQLQuery:\s*(.*)", response_text, re.DOTALL)

        if sql_query_match:
            # Extract SQL query
            sql_query = sql_query_match.group(1).strip()

            # Cleaning up duplicate queries: If two queries appear, retain only the first one.
            sql_query = re.split(r';\s*SELECT', sql_query)[0] + ';'

            # Remove unnecessary quotes around column and table names (like "table"."column")
            sql_query = re.sub(r'\"(\w+)\"', r'\1', sql_query)

            # Fix misplaced quotes (e.g., after column names like "school_name")
            sql_query = re.sub(r'\"(\w+)\",', r'\1,', sql_query)
            sql_query = re.sub(r'\",', ',', sql_query)  # Remove extra quotes near commas

            # Remove any remaining unbalanced quotes
            sql_query = re.sub(r'\"(\w+)\s*', r'\1 ', sql_query)
            sql_query = re.sub(r'\s*\"(\w+)', r' \1', sql_query)

            # Remove any remaining escaped characters or backslashes
            sql_query = sql_query.replace("\\", "")

            # Remove any duplicate semicolons
            sql_query = re.sub(r';+', ';', sql_query).strip()

            # Ensure query ends with a single semicolon
            if not sql_query.endswith(';'):
                sql_query += ';'

            # Final trim to clean up any extraneous spaces
            sql_query = sql_query.strip()

            return sql_query

        else:
            raise ValueError("No SQL query found in the response.")

    except Exception as e:
        print(f"Error extracting SQL from response: {str(e)}")


async def generate_sql_and_execute(question, conn):
    try:
        if not conn:
            raise ValueError("Database connection not established. Please connect first.")

        # Define a function to create and run the SQL queries chain synchronously
        def run_sql_chain(connection):
            # Langchain requires a synchronous SQLDatabase connection
            db = SQLDatabase(connection)

            # Create the SQL query chain using the ChatGroq and LLM
            sql_chain = create_sql_query_chain(groq_llm, db)

            # Execute the query chain with the user's question
            response = sql_chain.invoke({"question": question})

            print(response)

            # Extract the SQL query from the model response
            sql_query = extract_sql_from_response(response)
            if not sql_query:
                raise ValueError("Failed to extract SQL query from AI response")

            print(sql_query)

            return sql_query, response

        # Run the SQL generation and execution in synchronous mode using run_sync
        sql_query, response = await conn.run_sync(run_sql_chain)

        # Execute the SQL query asynchronously (use await)
        result = await conn.execute(text(sql_query))

        # Fetch all rows asynchronously
        rows = await result.fetchall()

        return {
            "sql_query": sql_query,
            "response": response,
            "result": rows
        }

    except Exception as e:
        print(f"Error in generating SQL with GROQ: {str(e)}")
        return None



def generate_plot_code_from_ai(result, question):
    """
    Generate Python Code for visualizing the SQL query result using AI.
    """
    formatted_sql_result = str(result)
    prompt = f"""
    You are connected to a database. The result of the SQL query is as follows:

    {formatted_sql_result}

    Based on this query result, generate Python code to create an appropriate
    visualization using Matplotlib or Seaborn.
    The code should be ready to execute.
    
    The user's question was: {question}
    """

    # Invoke the GROQ llm to generate the python code
    try:
        ai_response = groq_llm.invoke(prompt)
        raw_plot_code = ai_response.content  # The generated Python code

        print("Raw python code ", raw_plot_code)
        if not raw_plot_code:
            print("There was no raw plot code response")

        # Clean the AI-generated plot code before returning it
        cleaned_plot_code = clean_ai_plot_code(raw_plot_code)

        if not cleaned_plot_code:
            print(f"Unable to clean python code")

        return cleaned_plot_code
    except Exception as e:
        print(f"Error invoking AI for plot code generation : {str(e)}")
        return None
