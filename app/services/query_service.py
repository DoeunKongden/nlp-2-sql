import langchain_core.output_parsers
from sqlalchemy import text
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema.output_parser import StrOutputParser
import os
from langchain_core.prompts import PromptTemplate
import re

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

groq_llm = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0.7,
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


def extract_sql_query(response_text):
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


# function that will generate the plotting code
def get_ai_plot_code(db_type, question, results):
    result_str = str(results)
    # Use the AI to generate Python code for plotting the database
    generate_code_prompt = f"""
    You are connected to a {db_type} database. You have already retrieved the following data: {result_str}. 
    Your task is to generate **only** the Python code using Matplotlib or Seaborn to create a plot that visualizes this data based on the user's question: {question}.
    Do NOT include any comments, explanations, or extra text like "Here's the code." Return only the Python code, and nothing else.
    """

    code_response = groq_llm.invoke(generate_code_prompt)

    # Strip out any leading/trailing whitespace
    plot_code = code_response.content.strip()

    # Replace common placeholders like 'anime_data' with 'data'
    plot_code = plot_code.replace("anime_data", "data")

    # Remove escaped characters such as '\\n', '\n', and '\t'
    plot_code = plot_code.replace("\\n", "\n").replace("\\", "").replace("\\t", "\t").strip()

    # Additional cleanup: remove comments (lines starting with '#')
    plot_code = re.sub(r'#.*', '', plot_code)

    # Strip out any mark down code block markers like ```python and ```
    plot_code = plot_code.replace('```python', '').replace('```', '').strip()

    # Print the cleaned code for debugging
    print(f"Cleaned AI Plot Code: {plot_code}")

    # Basic validation to ensure the response looks like valid Python plotting code
    if not plot_code.startswith('plt.') and not plot_code.startswith('sns.'):
        raise ValueError("AI did not return valid Python code. Response received: " + plot_code)

    return plot_code

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


def convert_to_plain_language(result):
    if not result:
        return "I couldn't find any relevent information."
    response = "Here are the result"
    for row in result:
        row_text = ", ".join(f"{key}: {value}" for key, value in row.items())
        response += f"\n- {row_text}"
    return response
