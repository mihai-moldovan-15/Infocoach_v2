from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import time

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def upload_class_10_to_vector_store():
    """Upload all JSON files from class 10 to the vector store"""
    
    # Vector store ID for class 10
    vector_store_id = "vs_6851c43ad020819182dce3fa43d42afe"
    
    # Path to class 10 JSON files
    clasa_10_dir = os.path.join('resources', 'resurse_pbinfo', 'clasa_10_json')
    
    if not os.path.exists(clasa_10_dir):
        print(f"Directory {clasa_10_dir} not found!")
        return
    
    # Get all JSON files
    json_files = [f for f in os.listdir(clasa_10_dir) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON files in {clasa_10_dir}")
    
    # First, let's check the current vector store
    try:
        vector_store = client.vector_stores.retrieve(vector_store_id)
        print(f"Current vector store: {vector_store.name}")
        print(f"Status: {vector_store.status}")
        print(f"File counts: {vector_store.file_counts}")
        
        # If there are files, we might want to delete them first
        if vector_store.file_counts.total > 0:
            print(f"Vector store has {vector_store.file_counts.total} files")
            response = input("Do you want to delete existing files and re-upload? (y/n): ")
            if response.lower() == 'y':
                print("Deleting existing files...")
                # Delete all files in the vector store
                files = client.vector_stores.files.list(vector_store_id=vector_store_id)
                for file in files.data:
                    client.vector_stores.files.delete(
                        vector_store_id=vector_store_id,
                        file_id=file.id
                    )
                print("Existing files deleted.")
            else:
                print("Skipping deletion. Will add new files.")
        
    except Exception as e:
        print(f"Error checking vector store: {e}")
        return
    
    # Upload each JSON file
    uploaded_count = 0
    for json_file in json_files:
        file_path = os.path.join(clasa_10_dir, json_file)
        
        try:
            print(f"Uploading {json_file}...")
            
            # Upload the file
            with open(file_path, 'rb') as f:
                file = client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            # Add file to vector store
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file.id
            )
            
            uploaded_count += 1
            print(f"✓ Uploaded {json_file}")
            
            # Small delay to avoid rate limits
            time.sleep(1)
            
        except Exception as e:
            print(f"✗ Error uploading {json_file}: {e}")
    
    print(f"\nUpload completed! {uploaded_count} files uploaded.")
    
    # Check final status
    try:
        vector_store = client.vector_stores.retrieve(vector_store_id)
        print(f"Final vector store status: {vector_store.status}")
        print(f"Final file counts: {vector_store.file_counts}")
        
        if vector_store.status == "completed":
            print("✓ Vector store is ready for use!")
        else:
            print("⚠ Vector store is still processing...")
            
    except Exception as e:
        print(f"Error checking final status: {e}")

if __name__ == "__main__":
    upload_class_10_to_vector_store() 