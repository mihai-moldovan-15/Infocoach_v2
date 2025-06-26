import requests

def test_frontend_adaptation():
    try:
        response = requests.get('http://localhost:5000/api/problem_details?id=896')
        if response.status_code == 200:
            data = response.json()
            problem_type = data.get('problem_type', 'unknown')
            print(f"✅ API funcționează!")
            print(f"Tipul problemei: {problem_type}")
            
            if problem_type == 'subprogram':
                print("🎯 Frontend-ul va afișa:")
                print("  - Butonul: 'Testează subprogramul'")
                print("  - Mesaj informativ pentru subprograme")
            else:
                print("🎯 Frontend-ul va afișa:")
                print("  - Butonul: 'Rulează'")
                print("  - Interfața normală")
        else:
            print(f"❌ Eroare API: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare de conexiune: {e}")
        print("Asigură-te că serverul Flask rulează pe localhost:5000")

if __name__ == "__main__":
    test_frontend_adaptation() 