from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def test_lee_search():
    """Test search for 'algoritmul lui Lee' in the vector store"""
    
    vector_store_id = "vs_6851c43ad020819182dce3fa43d42afe"
    
    try:
        # Search for "algoritmul lui Lee"
        search_results = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query="algoritmul lui Lee",
            max_results=5
        )
        
        print(f"Search results for 'algoritmul lui Lee':")
        print(f"Found {len(search_results.data)} results\n")
        
        for i, result in enumerate(search_results.data, 1):
            print(f"Result {i}:")
            print(f"Score: {result.score}")
            print(f"Filename: {result.filename}")
            
            # Extract content from the result
            if hasattr(result, 'content') and result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        # Try to parse as JSON to get title
                        try:
                            import json
                            content_json = json.loads(content_item.text)
                            if 'title' in content_json:
                                print(f"Title: {content_json['title']}")
                        except:
                            pass
                        
                        # Show first 200 characters of content
                        text = content_item.text
                        if len(text) > 200:
                            text = text[:200] + "..."
                        print(f"Content preview: {text}")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error searching vector store: {e}")

if __name__ == "__main__":
    test_lee_search() 