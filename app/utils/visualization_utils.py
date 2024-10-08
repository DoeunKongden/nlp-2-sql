import logging
from langchain_groq import ChatGroq

# Initialize logger for debugging purposes
logger = logging.getLogger(__name__)

# Initialize Groq LLM
# Initialize Groq LLM
groq_llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
)


def detect_chart_type_with_llm(sql_result, question):
    """
    Uses the Groq LLM model to detect and return the appropriate chart type based on the SQL result.
    Args:
        sql_result (list): The SQL query result in list format.
        question (str): The user's natural language query.

    Returns:
        str: The chart type (e.g., 'bar', 'line', 'pie', etc.), with no additional text or comments.
    """

    formatted_sql_result = str(sql_result)

    # Prompt to the LLM to detect the chart type
    prompt = f"""
    The SQL query result is as follows:
    
    {formatted_sql_result}
    
    Based on this result and the user's question, '{question}', determine the most appropriate chart type to visualize this data.
    
    Return only the chart type (e.g., 'bar', 'line', 'pie', 'scatter''heatmap', etc.) without any extra response, comments, or text.)
    """
    try:
        logger.info(f"Invoking Groq LLM to detect chart type for visualization.")

        # Invoke the LLM with the prompt
        ai_response = groq_llm.invoke(prompt)

        # Checking if the AI response is valid
        if not ai_response or not ai_response.content:
            logger.error("No chart type was returned by the AI.")
            raise ValueError("Failed to detect chart type.")

        # Extract and clean the chart type (ensure no extra space or text)
        chart_type = ai_response.content.strip()

        logger.info(f"Detected chart type: {chart_type}")

        return chart_type
    except Exception as e:
        logger.error(f"Error detecting chart type: {str(e)}")
        return None