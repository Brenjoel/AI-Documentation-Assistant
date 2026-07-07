import os
import ssl 

import asyncio
from typing import Any , Dict , List

import certifi
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_tavily import TavilyCrawl, TavilyExtract, TavilyMap

from logger import (Colors , log_error, log_header ,log_info,log_success,log_warning)


load_dotenv()
Ollama_embedding_model = "nomic-embed-text"


# Configure SSL context to use Certifi certifications
ssl_context = ssl.create_default_context(cafile=certifi.where())
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

embeddings = OllamaEmbeddings(
    model = Ollama_embedding_model
)
# For openAI models you can use the following parameters , chunk_size = 50, retry_min_seconds=10, show_progress_bar= True

vector_store = Chroma(persist_directory = "chroma_db" , embedding_function= embeddings)
# vector_store = PineconeVectorStore(index_name=os.environ["INDEX_NAME"], embedding=embeddings)
tavily_extract = TavilyExtract()
tavily_map = TavilyMap(max_depth = 5, max_breadth = 20 , max_pages = 1000)
tavily_crawl = TavilyCrawl()


async def index_documents_async(documents : List[Document], batch_size: int = 50):
    """ Process documents in batches asyncronously"""
    log_header("VECTOR STORAGE PHASE")
    log_info(
        f"📚 VectorStore Indexing: Preparing to add {len(documents)} documents to vector store",
        Colors.DARKCYAN,
    )

    # Create batches
    batches = [
        documents[i: i+ batch_size] for i in range(0,len(documents), batch_size)
    ]

    log_info(
        f"📦 VectorStore Indexing: Split into {len(batches)} batches of {batch_size} documents each"
    )

    async def add_batch(batch: List[Document], batch_num: int)  :
        try: 
            await vector_store.aadd_documents(batch)
            log_success(
                f"VectorStore Indexing: Successfully added batch {batch_num}/{len(batches)} ({len(batch)} documents)"
            )
        except Exception as e:
            log_error(f"Vectorstore Indexing: Failed to add batch {batch_num} - {e}")
            return False
        return True
    
    #  Process batches concurrently
    
    # tasks = [
    # add_batch(batch, i+1)
    # for i, batch in enumerate(batches[:])
    # ]


    # for i, batch in enumerate(batches):
    #     await add_batch(batch, i+1)
    
    tasks = [add_batch(batch,i+1) for i,batch in enumerate(batches) ]
    results = await  asyncio.gather(*tasks , return_exceptions=True)
    # *tasks unpacks iterables ex: m = [1,2,3] print(*m) o/p = 1 2 
    

    # Count successful batches
    successful = sum(1 for result in results if result is True)

    if successful == len(batches):
        log_success(
            f"VectorStore Indexing: All batches processed successfully! ({successful}/{len(batches)})"
        )
    else:
        log_warning(
            f"VectorStore Indexing: Processed {successful}/{len(batches)} batches successfully"
        )
    

async def main():
    """Main async function to orchestarates the entire process"""
    log_header("DOCUMENTAION INGESTION PIPELINE")

    log_info(
        "TavilyCrawl: Starting to Crawl documentation",Colors.PURPLE
    )

    # crawl he documentaion site
    res = tavily_crawl.invoke(
        {
            "url" : "https://python.langchain.com/",
            "max_depth":3,
            "extract_depth": "advanced",
            "instructions":"ALL" # give any insrtruction to get the results based on the instructions Ex: "content on AI agents"
        }
    )

    all_docs = res['results'] # lsit of dictionaries containing keuys as url and  raw_content of url fetched
    # all_docs = [result for result in res['results']] #
    all_docs = [Document(page_content=result['raw_content'], metadata= {"source":result['url']}) for result in res['results'] ]
    # first we fetch the raw data from each url and then convert it into Document object and the url from where it is etched as metadata. This clearly informs where the data was fetched from
    log_success(f"TavilyCrawl: Successfully ceawked {len(all_docs)} urls from documentation site")
    
     # Split documents into chunks
    log_header("DOCUMENT CHUNKING PHASE")
    log_info(
        f"✂️  Text Splitter: Processing {len(all_docs)} documents with 1000 chunk size and 200 overlap",
        Colors.YELLOW,
    )

    text_splitters = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splitted_docs = text_splitters.split_documents(all_docs)

    log_success(
        f"Text Splitter: Created {len(splitted_docs)} chunks from {len(all_docs)} documents"
    )

    # Process documents asynchronously
    await index_documents_async(splitted_docs,batch_size=15)

    log_header("PIPELINE COMPLETE")
    log_success("🎉 Documentation ingestion pipeline finished successfully!")
    log_info("📊 Summary:", Colors.BOLD)
    log_info(f"   • Documents extracted: {len(all_docs)}")
    log_info(f"   • Chunks created: {len(splitted_docs)} ")
    # (This number should match with the number in the change in reord count of pinecone) 

if __name__ == "__main__":
    asyncio.run(main())