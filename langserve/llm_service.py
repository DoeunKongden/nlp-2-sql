from langchain.llms import Groq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os


# Implementing SQL generation 
load_dotenv()

# Get the api key from the environment
api_key = os.getenv("GROQ_API_KEY")

groq_llm = Groq(api_key=api_key)

# Define a Langchain model that generates SQL queries
def generate_sql_chain():
    template = "Translate this question into a SQL query: {question}"
    prompt = PromptTemplate(template=template, input_variables=["question"])
    llm_chain = LLMChain(prompt=prompt, llm=groq_llm)
    return llm_chain