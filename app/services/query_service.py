import langchain_core.output_parsers
from sqlalchemy import text
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema.output_parser import StrOutputParser
import os
from langchain_core.prompts import PromptTemplate

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

groq_llm = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# Defining prompt template 
prompt_template = """
You are connected to a {db_type} database. Generate an SQL query to answer the following question:
{question}
"""
prompt = PromptTemplate.from_template(prompt_template)


def extract_sql_query(response_text):
    print("AI Response : ", response_text)
    try:
        # Check if the response contains code block markers ```sql
        if "```sql" in response_text:
            # Find the part after the opening ```sql
            sql_query = response_text.split("```sql")[1]
            # Find the part before the closing ```
            sql_query = sql_query.split("```")[0].strip()
        else:
            # If no code block markers, try extracting the SQL query directly
            start = response_text.lower().find("select")
            end = response_text.find(";") + 1
            if start != -1 and end != -1:
                sql_query = response_text[start:end].strip()
            else:
                return "SQL query not found in the response."

        # Remove any escaped underscores (i.e., convert `table\_name` to `table_name`)
        sql_query = sql_query.replace("\\_", "_")

        # Perform final cleanup and formatting if necessary
        sql_query = sql_query.replace("\\n", "\n").replace("\\t", "\t").strip()

        return sql_query

    except IndexError:
        # If the response doesn't have the expected format, return an error message
        return "SQL query not found in the response."





# function that will generate the SQL queries
def generate_sql_from_question(db_type,question):
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
def execute_sql(engine,query):
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