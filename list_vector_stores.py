from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

vector_stores = client.vector_stores.list()
for vs in vector_stores.data:
    print(f"Nume: {vs.name} | ID: {vs.id}")
    
#Nume: infocoach_clasa_9 | ID: vs_68336c8213308191949fbb3b53d20e67
#Nume: infocoach_clasa_11-12 | ID: vs_68336c5facbc8191becf60fe5b02fa8e
#Nume: infocoach_clasa_10 | ID: vs_68336c5f54748191bc3a4e9e632103a4