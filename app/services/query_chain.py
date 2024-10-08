import re
import time
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain.sql_database import SQLDatabase
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
from app.services.query_service import execute_sql
from app.utils.clean_ai_plot_code import clean_ai_plot_code
import ast
import logging
from app.utils.sql_utils import get_database_schema
from app.utils.visualization_utils import detect_chart_type_with_llm

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set logging level to INFO or DEBUG as needed

# You can also configure logging to a file or console if needed
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

# llm = Ollama(model="llama3.2")

groq_llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
)


def validate_python_code(python_code):
    """
        Validate the python code syntax without executing it, using the ast module.
        Return True if the code is valid, otherwise return the error message.
    """
    try:
        # Parse the python code using ast.parse
        ast.parse(python_code)
        return True
    except SyntaxError as e:
        # If there is a syntax error, return a detailed error message
        return f"Syntax Error: {e.msg} at line {e.lineno}, colum {e.offset}"
    except Exception as e:
        # Catch any other exception
        return f"An error occurred: {str(e)}"


def extract_sql_from_response(response_text):
    """
    Extract the SQL query from the AI's response text.
    """
    try:
        # Use regex to capture the SQL query
        sql_query_match = re.search(r"(SELECT[\s\S]*?ORDER BY.*?;)", response_text, re.DOTALL)

        if sql_query_match:
            # Extract the SQL query from the matched group (group 1 is the actual query)
            sql_query = sql_query_match.group(1).strip()

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

        # Get the schema of the connected database
        schema = get_database_schema(engine)

        # Build a dynamic schema description for the LLM
        schema_description = "\n".join([f"{table}: {', '.join(columns)}" for table, columns in schema.items()])

        # Custom prompt to guide the LLM for better SQL generation based on the discovered schema
        prompt = f"""
        The user has asked the following question:

        '{question}'

        Generate a valid SQL query based on the schema of the database provided. The schema contains the following tables and columns:

        {schema_description}

        Ensure the SQL query is properly formatted and includes all necessary clauses (SELECT, FROM, WHERE, GROUP BY, ORDER BY). The query should group results by the correct columns and should be ready to execute.

        **Important Instructions**:
        - Return **only** the SQL query, without any explanation, comments, or additional text.
        - Do **not** include phrases like "Here is the SQL query" or any other extraneous information.
        - The output should contain the SQL query only.
        """

        # Create the SQL query chain using the ChatGroq as the LLM
        sql_chain = create_sql_query_chain(groq_llm, db)

        # Execute the query chain with user's question
        response = sql_chain.invoke({"question": prompt})

        print(response)

        # Executing the sql queries
        result = execute_sql(engine, response)
        if not result or len(result) == 0:
            logger.warning("No data found for the query. There might be no matching records.")
            return {
                "error": "No data found for the query. Please refine your question or check your data in the databse."}

        print(f"SQL result {result}")

        return {
            "response": response,
            "result": result
        }

    except Exception as e:
        print(f"Error in generating SQL with GROQ: {str(e)}")
        return {"error": str(e)}


def generate_plot_code_from_ai(result, question, max_retries=10, sleep_interval=1):
    """
    Generate Python code for visualizing the SQL query result using AI, with retries if code generation fails.
    Args:
        result (dict): The result of the executed SQL query.
        question (str): The question asked the AI model.
        max_retries (int): Maximum number of attempts to generate the code if it fails.
        sleep_interval (int): Time (in seconds) to wait between retries.

    Returns:
        str: The cleaned and validated Python code for visualization, or None if it fails.
    """
    retry_count = 0

    # Detect the chart type using the new LLM-based function
    chart_type = detect_chart_type_with_llm(result, question)

    if not chart_type:
        logger.error(f"Failed to detect chart type using LLM.")
        return None

    # Log the detected chart type
    logger.info(f"Detected chart type: {chart_type}")

    formatted_sql_result = str(result)
    prompt = f"""
    The SQL query result is as follows:

    {formatted_sql_result}

    Based on this query result, generate only Python code to create a professional and error-free {chart_type} visualization using Seaborn or Matplotlib. Ensure that the Python code:

    1. Converts any list or dictionary data into a Pandas DataFrame before plotting.
    2. Follows correct Python syntax and avoids errors such as incorrect data types or missing imports.
    3. If the data contains `Decimal` types, make sure to import the `decimal` module (`from decimal import Decimal`) and convert all Decimal values to `float`.
    4. Uses Seaborn for plotting, with a modern style like 'darkgrid' and a color palette such as 'Blues' or 'viridis'.
    5. Sets the figure size to at least (14, 10) for better readability.
    6. Includes descriptive titles, axis labels, and gridlines. Titles should be placed before keyword arguments in function calls (e.g., `plt.title('Title', fontsize=20)`).
    7. For bar plots, adds labels on top of the bars to show the exact values by iterating over the bars.
    8. Ensures x-axis labels are rotated if necessary to prevent overlap.
    9. Saves the plot as a PNG image with high resolution (300 dpi).
    10. **Return only the Python code. Do not include any extra text, language identifiers (like 'Python:'), or comments**.
    11. Do **not** include any comments or explanations, and ensure the output is **only** valid Python code ready to execute.

    The user's question was: {question}
    """

    # Retry loop to generate Python plot code
    while retry_count < max_retries:
        try:
            # Log before invoking the AI
            logger.info(f"Attempt {retry_count + 1}: Invoking AI to generate Python code for visualization.")

            # AI invocation
            ai_response = groq_llm.invoke(prompt)

            # Check if the AI response is valid
            if not ai_response or not ai_response.content:
                logger.error(f"AI Response is empty or invalid: {ai_response}")
                raise ValueError("No plot code was generated by the AI.")

            # Log the raw AI response
            logger.info(f"AI Response: {ai_response.content}")

            raw_plot_code = ai_response.content  # The generated Python code

            # Check if raw plot code is empty
            if not raw_plot_code:
                raise ValueError("No raw plot code response from AI.")

            logger.info(f"Raw plot code generated by AI: {raw_plot_code}")

            # Clean the AI-generated plot code
            cleaned_plot_code = clean_ai_plot_code(raw_plot_code)
            logger.info(f"Cleaned plot code: {cleaned_plot_code}")

            if not cleaned_plot_code:
                raise ValueError("Unable to clean Python code.")

            # Validate the cleaned python code
            validation_result = validate_python_code(cleaned_plot_code)
            if validation_result is not True:
                raise ValueError(f"Invalid Python Code: {validation_result}")

            logger.info("Python code generation and validation successful.")
            return cleaned_plot_code

        except Exception as e:
            retry_count += 1
            logger.error(f"Error generating the Python code (Attempt {retry_count}/{max_retries}): {str(e)}")

            if retry_count >= max_retries:
                logger.error(f"Maximum retries ({max_retries}) reached. Failing the operation.")
                return None

            # Wait before retrying
            logger.info(f"Retrying in {sleep_interval} seconds...")
            time.sleep(sleep_interval)

    return None
