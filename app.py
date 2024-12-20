import os
import streamlit as st
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq

st.title("Q&A with Gemma Model via GroqAPI")

# Load the GROQ API KEY
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key and "GROQ_API_KEY" in st.secrets:
    groq_api_key = st.secrets["GROQ_API_KEY"]

if not groq_api_key:
    st.error("Please set your GROQ_API_KEY as an environment variable or in Streamlit secrets.")
    st.stop()

# Load the GOOGLE_API_KEY
google_api_key = os.getenv('GOOGLE_API_KEY')
if not google_api_key and "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]

if not google_api_key:
    st.error("Please set your GOOGLE_API_KEY as an environment variable or in Streamlit secrets.")
    st.stop()

@st.cache_resource(show_spinner=True)
def load_data_and_build_vectorstore():
    # Load the PDFs from the folder
    loader = PyPDFDirectoryLoader("./data_source")
    documents = loader.load()

    # Split the documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(documents)

    # Use Google Gemma (Generative AI) Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001"
    )

    # VectorStore Creation
    vectorstore = FAISS.from_documents(final_documents, embeddings)
    return vectorstore

@st.cache_resource(show_spinner=True)
def load_llm():
    # Use ChatGroq with Gemma model
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name="gemma2-9b-it"
    )
    return llm

with st.spinner("Loading data and building vectorstore..."):
    vectorstore = load_data_and_build_vectorstore()

with st.spinner("Loading language model..."):
    llm = load_llm()

retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

prompt_template = """
Use the following piece of context to answer the question asked.
Please try to provide the answer only based on the context

{context}
Question:{question}

Helpful Answers:
"""

prompt = PromptTemplate(template=prompt_template, input_variables=["context","question"])

retrievalQA = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt}
)

st.write("Ask question:")
query = st.text_input("Enter your query", "")

if st.button("Get Answer") and query.strip():
    with st.spinner("Processing your query..."):
        result = retrievalQA.invoke({"query": query})
        st.write("**Answer:**")
        st.write(result['result'])

        with st.expander("Source Documents"):
            for doc in result['source_documents']:
                st.write(doc.page_content)
                st.write("---")