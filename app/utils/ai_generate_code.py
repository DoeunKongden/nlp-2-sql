from sqlalchemy import text
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
from langchain_core.prompts import PromptTemplate

from app.utils.clean_ai_plot_code import clean_ai_plot_code

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


def get_ai_plot_code(db_type, question, results):
    result_str = str(results)

    print("Result of queries execution ", result_str)
    # Use the AI to generate Python code for plotting the database
    generate_code_prompt = f"""
    You are connected to a {db_type} database. You have already retrieved the following data: {result_str}. 
    Your task is to generate **only** the Python code using Matplotlib or Seaborn to create a plot that visualizes this data based on the user's question: {question}.
    Do NOT include any comments, explanations, or extra text like "Here's the code." Return only the Python code, and nothing else.
    """
    code_response = groq_llm.invoke(generate_code_prompt)

    print("RAW AI response : ", code_response.content)

    # Clean the AI-generated code using the separate cleaning function
    plot_code = clean_ai_plot_code(code_response.content.strip())

    # Print the cleaned code for debugging
    print("Clean AI Code", plot_code)

    # Validation: Ensure the response contains valid Python plotting commands
    if "plt." not in plot_code and "sns." not in plot_code:
        raise ValueError("AI did not return valid Python code. Response received: " + plot_code)

    return plot_code
