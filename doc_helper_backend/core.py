import os
from typing import Any, Dict
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_pinecone import PineconeVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# Initialize embeddings
ollama_embeddings_model = "nomic-embed-text"
# ollama_model = 'qwen3:0.6b'
ollama_model = 'qwen3:8b'
# ollama_model = 'gemma3:270m' # Does not support tools

embeddings = OllamaEmbeddings(model = ollama_embeddings_model)

# Initialize Vectore store
# vectorstore = PineconeVectorStore(index_name=os.environ['INDEX_NAME'],embedding=embeddings)
vectorstore = Chroma(persist_directory="chroma_db",embedding_function=embeddings,)
# Initialize chat model
model = init_chat_model(model = "qwen/qwen3-32b", model_provider='groq')

@tool(response_format='content_and_artifact')
def retrieve_context(query: str):
    """Retrieve relatvent documentation to help answer user queries"""
    
    # Retrieve top 4 most similar documents
    retrieved_docs = vectorstore.as_retriever().invoke(query,k=3)

    # Serialize documents for model
    serialized = '\n\n'.join(
        (f"Source: {doc.metadata.get('source','Unknown')} \n\n Content: {doc.page_content}")
        for doc in retrieved_docs
    )

    # Return both serializes content and raw documents
    return serialized, retrieved_docs

def run_llm(query:str) -> Dict[str,Any]:
    """
    Run the RAG pipeline to answer the query using retrieved documentation.
    
    Args:
        query: The user's question

    Returns:
        Dictionary containing:
            - answer: The generated answer
            - context: list of retrieved documents
    
    """
    # Create the agent with retrieval tool
    system_prompt=(
        "You are a helpful AI assistant that answers questions about Langchain documentation."
        "You have access to a tool that retrieves relevent documentation."
        "STRICTLY Use the tool to find the relevent information before answering questions."
        "Dont come to the final answer without making a tool call"
        "Always cite the sources you use in your answers."
        "If you cannot find the answer in the retrieved documentation, say so"
    )

    agent = create_agent(model, tools =[retrieve_context],system_prompt = system_prompt)

    # Build message List
    messages = [{'role':'user' , 'content':query}]

    # Invoke the agent
    response = agent.invoke({"messages":messages})

    # Extract the answer from the last AI message
    answer = response['messages'][-1].content

    # Extract context documents from the ToolMessage artifacts
    context_docs = []
    for message in response['messages']:
        # Check if thus is a ToolMessage with artifact
        if isinstance(message, ToolMessage) and hasattr(message,"artifact"):
            # The artifact should contain the list of document objects
            if isinstance(message.artifact, list):
                context_docs.extend(message.artifact)
                print("Tool message exists")
    
    return {
        'answer':answer,
        "context" : context_docs
    }

if __name__ == '__main__':
    result = run_llm(query="What are deep agents?")
    print(result)