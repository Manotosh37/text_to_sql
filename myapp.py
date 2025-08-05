import os
import streamlit as st
import re
import pymysql
from langchain.chains import create_sql_query_chain
from langchain_google_genai import GoogleGenerativeAI
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv() 

response = []

db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
db_port = int(os.getenv("DB_PORT", 56065))


with st.sidebar:
    st.title("Database Configuration")
    
    # Connection form
    db_host = st.text_input("Host", value=db_host)
    db_port = st.number_input("Port", value=db_port)
    db_user = st.text_input("Username", value=db_user)
    db_password = st.text_input("Password", value=db_password, type="password")
    db_name = st.text_input("Database", value=db_name)
    
    st.markdown("---")
    st.info("Current configuration will be used for the next query")

# Create SQLAlchemy engine with proper SSL configuration
engine = create_engine(
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
    connect_args={
        "ssl": {
            "ssl_mode": "REQUIRED",
            "ssl_ca": "/path/to/ca-cert.pem"  # You may need to provide the CA cert
        }
    }
)


# Initialize SQLDatabase
db = SQLDatabase(engine, sample_rows_in_table_info=3)

# Initialize LLM
llm = GoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.environ["GOOGLE_API_KEY"])

# Create SQL query chain
chain = create_sql_query_chain(llm, db)

def execute_query(question):
    try:
        # Generate SQL query from question
        response = chain.invoke({"question": question})
        match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        
        if not match:
            st.error("No valid SQL query found in response!")
            return None, None
        
        cleaned_query = match.group(1).strip()                
        result = db.run(cleaned_query)
        return cleaned_query, result

    except ProgrammingError:
        st.error("The query couldn't be executed. Please try a different question.")
        return None, None            
    except ProgrammingError as e:
        st.error("Something went wrong. Please try again.")
        return None, None

# Streamlit interface
st.title("Question Answering App")

# Input from user
question = st.text_input("Enter your question:")

if st.button("Execute"):
    if question:
        cleaned_query, query_result = execute_query(question)
        
        if cleaned_query and query_result is not None:
            st.write("Generated SQL Query:")
            st.code(cleaned_query, language="sql")
            st.write("Query Result:")
            st.write(query_result)
        else:
            st.write("No result returned due to an error.")
    else:
        st.write("Please enter a question.")
        
