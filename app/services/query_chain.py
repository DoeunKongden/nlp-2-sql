import re
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain.sql_database import SQLDatabase
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

from app.services.query_service import execute_sql
from app.utils.clean_ai_plot_code import clean_ai_plot_code
from app.utils.sql_extraction import extract_sql_query

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


def extract_sql_from_response(response_text):
    """
       Extract the SQL query from the AI's response text.
    """
    try:
        # Use regex to find SQL query more accurately
        sql_query_match = re.search(r"SQLQuery: (.*?);", response_text, re.DOTALL)
        if sql_query_match:
            # Extract the SQL query from the matched group and clean any extra spaces
            sql_query = sql_query_match.group(1).strip() + ";"

            # Specifically replace escaped double quotes (\") with regular double quotes (")
            sql_query = sql_query.replace(r'\"', '"')

            # Remove any remaining backslashes
            sql_query = sql_query.replace('\\', '')

            # Ensure there are no double spaces after cleanup
            sql_query = re.sub(' +', ' ', sql_query)

            return sql_query
        else:
            raise ValueError("No SQL query found in the response.")

    except Exception as e:
        print(f"Error extracting SQL from response: {str(e)}")
        return None


def generate_sql_and_execute(question, engine):
    try:
        if not engine:
            raise ValueError("Database connection not established. Please connect first.")

        # Create Langchain SQLDatabase object using the engine
        db = SQLDatabase(engine)

        # Create the SQL query chain using the ChatGroq as the LLM
        sql_chain = create_sql_query_chain(groq_llm, db)

        # Execute the query chain with user's question
        response = sql_chain.invoke({"question": question})

        print(response)

        # Extract the sql query from the model response
        sql_query = extract_sql_query(response)
        if not sql_query:
            raise ValueError("Failed to extract SQL query from AI response")

        print(sql_query)

        # Executing the sql queries
        result = execute_sql(engine, sql_query)
        if not result:
            raise ValueError("There was no valid SQL queries to execute.")

        print(f"SQL result {result}")

        print(f"Generated SQL Query: {sql_query}")

        return {
            "sql_query": sql_query,
            "response": response,
            "result": result
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

    Based on this query result, generate Python code to create an appropriate visualization using Matplotlib or Seaborn.
    The code should be ready to execute.
    
    The user's question was: {question}
    """

    # Invoke the GROQ llm to generate the python code
    try:
        ai_response = groq_llm.invoke(prompt)
        raw_plot_code = ai_response.content  # The generated Python code

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
