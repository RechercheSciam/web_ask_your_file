# Setting uo the environment
#!pip3 install streamlit
#!pip3 install langchain #==0.0.154
#!pip3 install PyPDF2 #==3.0.1
#!pip3 install faiss-cpu #==1.7.4
#!pip3 install openai
#!pip3 install -qU langchain tiktoken tqdm
#!pip3 install PyMuPDF
#!pip3 install pypdf
#!pip3 install pandas

#!pip3 install docx2txt
#!pip3 install odfpy
#!pip3 install python-pptx
#!pip3 install python-docx


import os, sys, io
from dotenv import load_dotenv
import streamlit as st
import tempfile

import posixpath
import time
from tqdm.auto import tqdm
from PyPDF2 import PdfReader
import docx2txt,openpyxl,docx
import pandas as pd
from pptx import Presentation
from docx import Document
from odf.opendocument import load
from odf import teletype
from odf import text as odf_text


import fitz

# Use langchain to use question answer based chaining
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.callbacks import get_openai_callback
from langchain.memory import ConversationBufferMemory


load_dotenv()

# Get OPENAI API key
OPENAI_API_KEY = ""

#
def read_file(file):
  extension = file.name.split('.')[-1].lower()
  text = " "

  # Read the file once and store the contents in a variable
  #file = io.BytesIO(file.read())

  # PDF
  if extension == 'pdf':
    file = io.BytesIO(file.read())
    file.seek(0)
    doc = fitz.open("pdf",file.read())
    for page in doc:
        text += page.get_text()

  # Word Document
  elif extension == 'docx':
    file = io.BytesIO(file.read())
    file.seek(0)
    doc = docx.Document(file)
    text = " "
    for page in doc.paragraphs:
        text += page.text
  # CSV
  elif extension == 'csv':
    file = file.read().decode("utf-8")
    read = pd.read_csv(io.StringIO(file))
    text += " ".join(read.astype(str).values.flatten())

  # Excel
  elif extension == 'xlsx':
    doc = pd.read_csv(file)
    text = doc.to_string(index=False, header=False)

  # Text
  elif extension == 'txt':
    text = file.read().decode('utf-8')

  # PowerPoint
  elif extension == 'pptx':
    doc = Presentation(io.BytesIO(file.read()))

    for slide in doc.slides:
      for shape in slide.shapes:
        if shape.has_text_frame:
          for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
              text += run.text + " "

  # Odt
  elif extension == 'odt':
    doc = load(file)
    all_paragraphs = doc.getElementsByType(odf_text.P)
    for paragraph in all_paragraphs:
      text += teletype.extractText(paragraph)

  else:
    print(f'Document format {file} is not supported!')
    return None

  return text


def main():
    st.set_page_config(page_title="Ask your file",
                       page_icon="📚",
                       initial_sidebar_state="auto",
                       )
    
    st.header("Ask your file -- version: text Sciam --")

    file_types = ["pdf","pptx","txt","csv","odt","xlsx","docx"]

    uploaded_file = st.file_uploader("Upload your file",type=file_types)

    hide_streamlit_style = """
            <style>
            
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

    if uploaded_file is not None:
        # Display file name
        st.write(f"File uploaded: {uploaded_file.name}")

        # Ensure the uploaded_file is at the start of the file
        #uploaded_file.seek(0)
        text = read_file(uploaded_file)

        if text is None:
          st.write("Failed to read file.")
        else:
          st.write(f'File sample {text[:200]}')

        # split into chunks
        text_splitter = CharacterTextSplitter(
                separator = "\n",
                chunk_size = 1000,
                chunk_overlap = 200,
                length_function = len
        )
        
        chunks = text_splitter.split_text(text)

        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        knowledge_base = FAISS.from_texts(chunks, embeddings)

        # User question
        #user_question = st.tetx_input("Ask a question: ")

        user_input = st.text_area(
                "Ask the document "
            )
        #Use bullet points and make it more user friendly read
        prompt_engineering = """ Use the following format:\
                    Format your response as paragraphs, use bullet points\
                    Write in a concise, professional and unambigous tone.      
        """
        prompt = f""" {user_input}.
                  '''{prompt_engineering}'''
                  """
        
        if st.button("Generate Q&A"):
          docs = knowledge_base.similarity_search(prompt)
          llm = OpenAI(openai_api_key=OPENAI_API_KEY)
           
          chain = load_qa_chain(llm,
                                chain_type="stuff"
                              )
           
          response = chain.run(input_documents = docs, question = prompt)
          st.markdown("### Generated Answer ")
          st.write(response)

if __name__ == "__main__":
   main()
           
######
# SCIAM @08/2023






