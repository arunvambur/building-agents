


import asyncio
import os
from typing import Sequence

from langchain_chroma import Chroma
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


UK_DESTINATIONS = [
    "Cornwall",
    "North_Cornwall",
    "South_Cornwall",
    "West_Cornwall",
]

async def build_vectorstore(destinations: Sequence[str]) -> Chroma:
    """Download Wikivoyage pages and create a Chroma vector store."""
    urls = [f"https://en.wikivoyage.org/wiki/{slug}" for slug in destinations]
    
    loader = AsyncHtmlLoader(urls)
    print("Downloading destination pages ...")
    docs = await loader.aload()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=128)
    chunks = sum([splitter.split_documents([d]) for d in docs], [])

    print(f"Embedding {len(chunks)} chunks ...")
    vectordb_client = Chroma.from_documents(chunks, embedding=OpenAIEmbeddings())
    print("Vector store ready.\n")

    return vectordb_client

_ti_vectorstore_client: Chroma | None = None

def get_travel_info_vectorstore() -> Chroma:
    global _ti_vectorstore_client
    if _ti_vectorstore_client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("""Set OPENAI_API_KEY env variable and re-run""")
        _ti_vectorstore_client = asyncio.run(build_vectorstore(UK_DESTINATIONS))

    return _ti_vectorstore_client

_ti_vectorstore_client = get_travel_info_vectorstore()
ti_retriever = _ti_vectorstore_client.as_retriever()



@tool(description="""Search travel information about destinations in England.""")
def search_travel_info(query: str)-> str:
    """Search embedded wikivoyage contnet for information about destinations in England."""
    docs = ti_retriever.invoke(query)
    top = docs[:4] if isinstance(docs, list) else docs
    return "\n--\n".join(d.page_content for d in top)