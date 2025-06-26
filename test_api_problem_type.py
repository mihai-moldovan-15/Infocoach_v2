import requests
import json

def test_api_problem_type():
    # Test cu problema FactorialF (ID: 896)
    response = requests.get('http://localhost:5000/api/problem_details?id=896')
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API funcționează!")
        print(f"Tipul problemei: {data.get('problem_type', 'N/A')}")
        print(f"Enunțul: {data.get('statement', 'N/A')[:100]}...")
    else:
        print(f"❌ Eroare API: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api_problem_type() 