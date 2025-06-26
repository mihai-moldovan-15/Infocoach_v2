import requests
import json

def test_subprogram_endpoint():
    """Testează endpoint-ul pentru testarea subprogramelor"""
    
    # Codul utilizatorului pentru funcția factorial
    user_code = """
int fact(int n) {
    if (n == 0) return 1;
    return n * fact(n - 1);
}
"""
    
    # Datele pentru test
    test_data = {
        'problem_id': 896,  # FactorialF
        'code': user_code,
        'custom_input': '4'  # Test cu factorial de 4
    }
    
    try:
        print("🧪 Testez endpoint-ul pentru subprograme...")
        response = requests.post('http://localhost:5000/api/test_subprogram', 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint funcționează!")
            print(f"Succes: {result.get('success')}")
            
            if result.get('success'):
                print(f"Output: {result.get('output')}")
                print("🎉 Subprogramul funcționează corect!")
            else:
                print(f"Eroare: {result.get('error')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
            print(f"Răspuns: {response.text}")
            
    except Exception as e:
        print(f"❌ Eroare de conexiune: {e}")
        print("Asigură-te că serverul Flask rulează pe localhost:5000")

if __name__ == "__main__":
    test_subprogram_endpoint() 