from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Test vector store for class 10
vector_store_id = "vs_6851c43ad020819182dce3fa43d42afe"

try:
    # Retrieve the vector store
    vector_store = client.vector_stores.retrieve(vector_store_id)
    print(f"Vector store name: {vector_store.name}")
    print(f"Vector store status: {vector_store.status}")
    print(f"File count: {vector_store.file_counts}")
    
    # Test search in the vector store
    search_result = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query="algoritmul fill",
        max_num_results=5
    )
    
    print(f"\nSearch results for 'algoritmul fill':")
    print(f"Found {len(search_result.data)} results")
    
    for i, result in enumerate(search_result.data):
        print(f"\nResult {i+1}:")
        print(f"Score: {result.score}")
        print(f"Result type: {type(result)}")
        print(f"Result attributes: {dir(result)}")
        # Try to access the content
        if hasattr(result, 'text'):
            print(f"Content: {result.text[:200]}...")
        elif hasattr(result, 'content'):
            print(f"Content: {result.content[:200]}...")
        else:
            print(f"Raw result: {result}")
        
except Exception as e:
    print(f"Error: {e}") 