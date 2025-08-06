import os
import streamlit as st
import re
import pymysql
from langchain.chains import create_sql_query_chain
from langchain_openai import ChatOpenAI
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
    
    db_host = st.text_input("Host", value=db_host)
    db_port = st.number_input("Port", value=db_port)
    db_user = st.text_input("Username", value=db_user)
    db_password = st.text_input("Password", value=db_password, type="password")
    db_name = st.text_input("Database", value=db_name)
    
    st.markdown("---")
    st.info("Current configuration will be used for the next query")

engine = create_engine(
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
    connect_args={
        "ssl": {
            "ssl_mode": "REQUIRED",
            "ssl_ca": "/path/to/ca-cert.pem"  # You may need to provide the CA cert
        }
    }
)


db = SQLDatabase(engine, sample_rows_in_table_info=3)



llm = ChatOpenAI(
    model="llama3-70b-8192",  # or "mixtral-8x7b-32768"
    temperature=0.3,
    max_tokens=1024,
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

chain = create_sql_query_chain(llm, db)

def execute_query(question):
    try:
        
        response = chain.invoke({"question": question})

        
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response, re.DOTALL)
        if not match:
            match = re.search(r"SQLQuery:\s*(SELECT .*?;)", response, re.IGNORECASE | re.DOTALL)
        if not match:
            match = re.search(r"(SELECT .*?;)", response, re.IGNORECASE | re.DOTALL)

        if not match:
            st.error("Couldn’t extract a SQL query. Try rephrasing your question.")
            st.text("Raw LLM Output:")
            st.code(response)
            return None, None

        cleaned_query = match.group(1).strip()

        result = db.run(cleaned_query)
        return cleaned_query, result

    except ProgrammingError as e:
        st.error("SQL Error")
        st.text(str(e))
        return None, None
    except Exception as e:
        st.error("Unexpected Error")
        st.text(str(e))
        return None, None


st.title("Question Answering App")


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
