from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def test_lee_search():
    """Test search for Lee algorithm in the vector store"""
    
    vector_store_id = "vs_6851c43ad020819182dce3fa43d42afe"
    
    try:
        # Search for "algoritmul lui Lee"
        search_results = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query="algoritmul lui Lee",
            max_num_results=5
        )
        
        print(f"Search results for 'algoritmul lui Lee':")
        print(f"Found {len(search_results.data)} results\n")
        
        for i, result in enumerate(search_results.data, 1):
            print(f"Result {i}:")
            print(f"Score: {result.score}")
            print(f"File: {result.file_id}")
            print(f"Content preview: {result.content[:200]}...")
            print("-" * 50)
        
        # Also test with "lee"
        print("\n" + "="*50)
        print("Search results for 'lee':")
        
        search_results2 = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query="lee",
            max_num_results=3
        )
        
        print(f"Found {len(search_results2.data)} results\n")
        
        for i, result in enumerate(search_results2.data, 1):
            print(f"Result {i}:")
            print(f"Score: {result.score}")
            print(f"File: {result.file_id}")
            print(f"Content preview: {result.content[:150]}...")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_lee_search() 