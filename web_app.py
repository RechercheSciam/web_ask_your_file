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
#!pip3 install pinecone-client openai tiktoken


import os, sys, io
import getpass
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
from langchain.text_splitter import CharacterTextSplitter,RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
# Add memory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

from langchain import PromptTemplate
from langchain.document_loaders import TextLoader, PyPDFLoader
import json
from langchain.document_loaders import PyPDFLoader, JSONLoader, UnstructuredHTMLLoader,UnstructuredExcelLoader
from langchain.document_loaders import UnstructuredPowerPointLoader, Docx2txtLoader, UnstructuredODTLoader
from langchain.document_loaders import UnstructuredURLLoader,WikipediaLoader
from langchain.document_loaders.csv_loader import CSVLoader

import pinecone


load_dotenv()


#Read the file 
def read_file(file):
	extension = file.split('.')[-1].lower()

	# Read the file once and store the contents in a variable
	# PDF
	if extension == 'pdf':
		print(f'Loading {file}')
		loader = PyPDFLoader(file)

	# Word Document
	elif extension == 'docx':
		print(f'Loading {file}')
		loader = Docx2txtLoader(file)

	# CSV
	elif extension == 'csv':
		print(f'Loading {file}')
		loader = CSVLoader(file)

	# Excel
	elif extension == 'xlsx':
		print(f'Loading {file}')
		loader = UnstructuredExcelLoader(file, mode="elements")

	# Text
	elif extension == 'odt':
		print(f'Loading {file}')
		loader = UnstructuredODTLoader(file, mode="elements")

	# PowerPoint
	elif extension == 'pptx':
		print(f'Loading {file}')
		loader = UnstructuredPowerPointLoader(file)

	# html
	elif extension == 'html':
		print(f'Loading {file}')
		loader = UnstructuredHTMLLoader(file) #url

	# json
	elif extension == 'json':
		print(f'Loading {file}')
		loader = json.loads(file.read_text()) #url
	else:
		print(f'The format file {file} is not supported.')
		return None

	data = loader.load()
	return data

# create chunks
def chunk_data(data, chunk_size=512, chunk_overlap=50):
	text_splitter = RecursiveCharacterTextSplitter(
								chunk_size = chunk_size,
								chunk_overlap = chunk_overlap,
				)
	chunks = text_splitter.split_documents(data)
	return chunks

# create embeddings
def create_embeddings(chunks,index="pdfsciam"):
	embeddings = OpenAIEmbeddings()
	vectorstore = Pinecone.from_documents(chunks, embeddings, index_name=index)

	return vectorstore

def create_llm_chain(vectorstore, question, k=3):
	docs = vectorstore.similarity_search(question,k=k)
	llm = ChatOpenAI()

	return llm

# run chain
def ask_with_memory(vectorstore, question, k, memory=[]):
	chain = ConversationalRetrievalChain.from_llm(
								llm=create_llm_chain(vectorstore, question, k),
								retriever=vectorstore.as_retriever(),
															)
	
	response = chain({"question": question, "chat_history":memory})
	memory.append((question,response['answer']))
	
	return response, memory


def clear_history():
	if 'history' in st.session_state:
		del st.session_state['history']


def main():
		# Get OPENAI API key
		OPENAI_API_KEY = "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"
		os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

		#Pinecone api_key
		PINECONE_API_KEY = "8f50afcb-3234-4914-b73f-9b6f57690074"
		os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

		PINECONE_ENV = "eu-west1-gcp"
		os.environ["PINECONE_ENV"]= PINECONE_ENV

		# initialize pinecone
		pinecone.init(
						 api_key=PINECONE_API_KEY,  # find at app.pinecone.io
						 environment=PINECONE_ENV,  # next to api key in console
						)

		st.image('./logo1.png')
		st.subheader('Ask your file.')

		with st.sidebar:
			uploaded_file = st.file_uploader('Upload a file: ', type=['pdf','docx','pptx','csv','odt','html','xlsx','json'])
			chunk_size = st.number_input('Chunk size: ',min_value=100,max_value=2048,value=512,on_change=clear_history)
			k = st.number_input('k',min_value=1, max_value=10,value=3,on_change=clear_history)

			add_data = st.button('Add Data',on_click=clear_history)

			if uploaded_file and add_data:
				with st.spinner('reading, chunking and embedding file ...'):
					bytes_data = uploaded_file.read()
					file_name = os.path.join('./', uploaded_file.name)

					with open(file_name, 'wb') as file:
						file.write(bytes_data)

					data = read_file(file_name)
					chunks = chunk_data(data, chunk_size=chunk_size)
					st.write(f'Chunk size: {chunk_size}, Chunks: {len(chunks)}')

					vectorstore = create_embeddings(chunks)

					st.session_state.vs = vectorstore
					st.success('File uploaded, chunked and embedded successfully.')
		
		q = st.text_input("Ask a question about the content of your file:")

		if q:
			if 'vs' in st.session_state:
				vectorstore = st.session_state.vs
				st.write(f'The number of most similar vector for answering the question: {k}')
				response, memory = ask_with_memory(vectorstore,q,k)
				st.text_area('LLL generated response: ',value=response["answer"])

				st.divider()

				if 'history' not in st.session_state:
					st.session_state.history = ' '
				value = f'Question: {q} \nAnswer: {response["answer"]}:'
				st.session_state.history = f'{value} \n {"-"*100}\n{st.session_state.history}'
				h = st.session_state.history
				st.text_area(label='Chat History', value=h, key='history', height=400)
					 	

if __name__ == "__main__":
	main()
					 
######
# SCIAM @08/2023






