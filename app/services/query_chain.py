from fastapi import HTTPException, status, responses
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
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

# llm = Ollama(model="llama3.2")

groq_llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0.7,
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
        sql_query_match = re.search(
            r"(SELECT[\s\S]*?ORDER BY.*?;)", response_text, re.DOTALL
        )

        if sql_query_match:
            # Extract the SQL query from the matched group (group 1 is the actual query)
            sql_query = sql_query_match.group(1).strip()

            # Specifically replace escaped double quotes (\") with regular double quotes (")
            sql_query = sql_query.replace(r"\"", '"')

            # Remove any remaining backslashes
            sql_query = sql_query.replace("\\", "")

            # Ensure there are no double spaces after cleanup
            sql_query = re.sub(" +", " ", sql_query)

            return sql_query
        else:
            raise ValueError("No SQL query found in the response.")

    except Exception as e:
        print(f"Error extracting SQL from response: {str(e)}")
        return None


def generate_sql_and_execute(question, engine, max_retries=5):
    """
    A function that will generate SQL from Text and execute them to get results.
    The result will then be responded back to the user in plain human language.
    """
    try:
        if not engine:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database connection is not established. Please connect to a database first.",
            )

        # Create Langchain SQLDatabase object using the engine
        db = SQLDatabase(engine)

        # Get the schema of the connected database
        schema = get_database_schema(engine)

        # Build a dynamic schema description for the LLM
        schema_description = "\n".join(
            [f"{table}: {', '.join(columns)}" for table, columns in schema.items()]
        )

        # Initialize retry mechanism variables
        attempt = 0
        error_message = ""

        while attempt < max_retries:
            attempt += 1

            # Updated prompt to generate SQL
            prompt = f"""
            Given an input question, create a syntactically correct SQL query based on the provided schema. The SQL query should be ready to run directly without needing any modifications.

            Use the following guidelines:

            1. Return only the SQL query. Do not include any additional text, comments, or explanations such as "Here is the SQL query".
            2. Ensure the SQL query uses the correct PostgreSQL syntax.
            3. If using columns that exist in multiple tables, fully qualify the column names with the table alias (e.g., "sales.product_name" instead of "product_name").
            4. Include all necessary clauses (e.g., SELECT, FROM, WHERE, GROUP BY, ORDER BY) and ensure the SQL query is correctly grouped when needed.
            5. Avoid referencing non-existent columns or tables. Always use valid column names from the provided schema.
            6. Use the correct JOIN clauses to reference related tables, ensuring that the join conditions are accurate.
            7. If any previous queries generated an error such as "{error_message}", ensure the new query addresses and avoids those errors (e.g., ambiguous columns, missing JOINs, incorrect grouping).
            8. Do not include any phrases like "Here is the SQL query", "SQL query to run", or "Answer". Only return the query itself.
            9. The SQL query should only contain SELECT statements.
            10. Do not generate any UPDATE, INSERT, or DELETE queries under any circumstances.

            The schema contains the following tables and columns:
            {schema_description}.

            The user has asked the following question:
            '{question}'

            Generate and return only the SQL query to answer this question.
            """

            try:
                # Generate the SQL query using the LLM
                sql_chain = create_sql_query_chain(groq_llm, db)
                response = sql_chain.invoke({"question": prompt}).strip()

                # Validate the SQL query to check for INSERT, UPDATE, DELETE
                def validate_sql_query(query: str):
                    disallowed_keywords = ["UPDATE", "DELETE", "INSERT"]
                    for keyword in disallowed_keywords:
                        if re.search(rf"\b{keyword}\b", query, re.IGNORECASE):
                            return keyword  # Return the detected keyword

                invalid_keyword = validate_sql_query(response)

                if invalid_keyword:
                    logger.error(
                        f"Unsafe query detected: We only allow SELECT records from the database, not {invalid_keyword.lower()} them."
                    )
                    # No retry for unsafe queries, raise an HTTP exception and terminate further execution
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"We only allow SELECT records from the database, not {invalid_keyword.lower()} them.",
                    )

                # If the query is valid, execute it
                result = execute_sql(engine, response)

                if not result or len(result) == 0:
                    logger.warning(
                        "No data found for the query. There might be no matching records."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No data found for the query. Please refine your question or check your database.",
                    )

                # Log the SQL execution result
                logger.info(f"SQL execution result: {result}")

                # Return the successful result
                return {"response": response, "result": result}

            except HTTPException as http_exc:
                # If HTTPException is raised, stop retries and return the error
                logger.error(f"Execution failed: {http_exc.detail}")
                raise http_exc  # This will exit the loop and return the error

            except Exception as e:
                # Capture any other errors during the process
                error_message = str(e)
                logger.error(f"Attempt {attempt} failed with error: {error_message}")

                # Max retries reached
                if attempt >= max_retries:
                    logger.error(f"Max retries reached. Last error: {error_message}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Max retries reached: {error_message}",
                    )

                # Retry with modified prompt based on error message
                logger.info(f"Retrying... (Attempt {attempt + 1}/{max_retries})")
    except HTTPException as e:
        # Raise HTTP Exception for general errors
        raise e

    except Exception as e:
        # Raise HTTP exception for general errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def generate_plot_code_from_ai(result, question, max_retries=5, sleep_interval=1):
    retry_count = 0
    error_message = ""
    incomplete_code = False

    # Detect the chart type using the new LLM-based function
    chart_type = detect_chart_type_with_llm(result, question)

    if not chart_type:
        logger.error(f"Failed to detect chart type using LLM.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to detect chart type for the given result.",
        )

    formatted_sql_result = str(result)

    while retry_count < max_retries:
        # Prepare the prompt for generating Python code
        prompt = f"""
        The SQL query result is as follows:

        {formatted_sql_result}

        Based on this query result, generate Python code to create a professional and error-free {chart_type} visualization using Seaborn or Matplotlib. Ensure that the Python code:

        1. Converts any list or dictionary data into a Pandas DataFrame before plotting.
        2. Only converts numeric values (e.g., Decimal types) to floats, but **avoids converting string columns** (like 'customer_name') into numeric values.
        3. Follows correct Python syntax and ensures the code is complete, avoiding errors such as unterminated strings, unmatched parentheses, and incomplete code.
        4. Uses Seaborn for plotting, with a modern style like 'darkgrid'. Ensure to apply styles using `sns.set_style("darkgrid")` and not as plot parameters.
        5. Sets the figure size to at least (14, 10) for better readability.
        6. Ensures valid format specifiers (such as `%.1f` for floating-point numbers) when displaying numeric values and avoids any incorrect or unsupported specifiers.
        7. Includes descriptive titles, axis labels (if applicable), and gridlines.
        8. Ensures x-axis labels are rotated if necessary to prevent overlap.
        9. For pie charts, ensures the percentages displayed are formatted correctly and labeled. Use `startangle=90` and `autopct='%.1f%%'` for proper labeling.
        10. Please add data labels to any visualization.
        11. If the user asks to exclude specific data (e.g., "exclude Product XX"), ensure that the excluded data is not part of the final plot. The exclusion should be based on what the user mentioned in the question.
        12. If the user asks to include only specific data (e.g., "include only Product XX and Product YY"), ensure that only the mentioned data is included in the final plot.
        13. Ensure the code is valid and complete before returning it. Avoid truncating the code in the middle of statements or leaving out required function calls like `plt.show()` or `plt.savefig()`.

        **Important**:
        - Ensure that the Python code is clean, follows best practices, and avoids deprecated or soon-to-be-deprecated features.
        - **Ensure to use `sns.set_style("darkgrid")` for Seaborn styles, and avoid using styles as parameters for plotting functions.**
        - If the previous error was "unterminated string literal", make sure all strings are properly closed and terminated.
        - If the previous error was "could not interpret value 'darkgrid' for 'style'", use `sns.set_style()` instead of passing it as a parameter to plotting functions.
        - If the user asked to exclude or include certain data points, ensure that the generated code handles these cases properly by filtering the dataset.
        - If the generated code is too large to fit in one response, generate it in parts. Return only the Python code. Do not include any extra text, language identifiers (like 'Python:'), or comments.
        - Do not include any language identifiers (like 'Python' or 'Python:')
        - Ensure the generated data is complete. If ellipsis (...) appears in the data, return the full data instead.

        The user's question was: {question}
        """

        try:
            logger.info(
                f"Attempt {retry_count + 1}: Invoking AI to generate Python code for visualization."
            )
            ai_response = groq_llm.invoke(prompt)

            if not ai_response or not ai_response.content:
                raise ValueError("No valid plot code was generated by the AI.")

            raw_plot_code = ai_response.content.strip()
            logger.info(f"Raw plot code generated by AI: {raw_plot_code}")

            if not raw_plot_code:
                raise ValueError("The generated plot code is empty.")

            if raw_plot_code.count("(") != raw_plot_code.count(
                ")"
            ) or raw_plot_code.count("[") != raw_plot_code.count("]"):
                incomplete_code = True
                raise ValueError("The generated code is incomplete or malformed.")

            cleaned_plot_code = clean_ai_plot_code(raw_plot_code)
            logger.info(f"Cleaned plot code: {cleaned_plot_code}")

            if not cleaned_plot_code:
                raise ValueError("Unable to clean the Python code.")

            validation_result = validate_python_code(cleaned_plot_code)
            if validation_result is not True:
                raise ValueError(f"Plot execution failed: {validation_result}")

            logger.info("Python code generation and execution successful.")
            return cleaned_plot_code

        except Exception as e:
            retry_count += 1
            error_message = str(e)
            logger.error(
                f"Error generating Python code (Attempt {retry_count}/{max_retries}): {error_message}"
            )

            if retry_count >= max_retries:
                logger.error(f"Maximum retries ({max_retries}) reached.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate plot code after {max_retries} attempts: {error_message}",
                )

            logger.info(f"Retrying in {sleep_interval} seconds...")
            time.sleep(sleep_interval)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate valid plot code after multiple attempts.",
    )
