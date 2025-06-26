import requests
import json

def test_complete_code_generation():
    """Testează generarea codului complet cu AI"""
    
    # Funcția utilizatorului cu greșeli intenționate
    user_code = """int fact(int n, int p=1)
{
    for(int i=1;i<=n;i++)
        p*=i
        retun p;
}"""
    
    # Testează și cu un warning (variabilă nefolosită)
    user_code_with_warning = """int fact(int n, int p=1)
{
    int unused_var = 42;  // Aceasta va genera un warning
    for(int i=1;i<=n;i++)
        p*=i;
    return p;
}"""
    
    # Datele pentru test
    test_data = {
        'problem_id': 896,  # FactorialF
        'code': user_code
    }
    
    try:
        print("🧪 Testez generarea codului complet...")
        response = requests.post('http://localhost:5000/api/generate_complete_code', 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint funcționează!")
            print(f"Succes: {result.get('success')}")
            
            if result.get('success'):
                complete_code = result.get('complete_code', '')
                print("\n📝 Codul complet generat:")
                print("=" * 60)
                print(complete_code)
                print("=" * 60)
                
                # Verifică dacă codul conține elementele necesare
                if '#include' in complete_code and 'main()' in complete_code and 'retun p;' in complete_code:
                    print("✅ Codul conține toate elementele necesare și păstrează greșelile!")
                else:
                    print("⚠️ Codul pare să nu conțină toate elementele necesare")
                    
            else:
                print(f"Eroare: {result.get('error')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
            print(f"Răspuns: {response.text}")
            
        # Testează și cu warning-uri
        print("\n🧪 Testez cu cod care generează warning-uri...")
        test_data_warning = {
            'problem_id': 896,
            'code': user_code_with_warning
        }
        
        response_warning = requests.post('http://localhost:5000/api/generate_complete_code', 
                                       json=test_data_warning,
                                       headers={'Content-Type': 'application/json'})
        
        if response_warning.status_code == 200:
            result_warning = response_warning.json()
            if result_warning.get('success'):
                print("✅ Codul cu warning-uri a fost generat cu succes!")
                complete_code_warning = result_warning.get('complete_code', '')
                if 'unused_var' in complete_code_warning:
                    print("✅ Codul conține variabila nefolosită (warning-ul va fi permis)")
            else:
                print(f"Eroare la generarea codului cu warning-uri: {result_warning.get('error')}")
        else:
            print(f"❌ Eroare HTTP la testul cu warning-uri: {response_warning.status_code}")
            
    except Exception as e:
        print(f"❌ Eroare de conexiune: {e}")
        print("Asigură-te că serverul Flask rulează pe localhost:5000")

if __name__ == "__main__":
    test_complete_code_generation() 