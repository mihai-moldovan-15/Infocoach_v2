import requests
import json

def test_debug_compilation():
    print("🔍 Debug compilare...")
    
    # Funcția ta exactă
    user_code = """int fact(int n, int p=1)
{
    for(int i=1;i<=n;i++)
        p*=i;
    return p;
}"""
    
    # Testează endpoint-ul
    url = "http://localhost:5000/test_subprogram"
    data = {
        "problem_id": 896,
        "user_code": user_code
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Răspuns primit:")
            print(f"Succes: {result.get('success')}")
            print(f"Output: {result.get('output', 'N/A')}")
            print(f"Error: {result.get('error', 'N/A')}")
            
            # Dacă există eroare, să vedem ce cod s-a trimis
            if result.get('error'):
                print("\n🔍 Verific codul trimis...")
                # Să verificăm ce cod se generează local
                from app import generate_test_code
                test_code = generate_test_code(896, user_code)
                if test_code:
                    print("📝 Codul generat local:")
                    print("=" * 50)
                    print(test_code)
                    print("=" * 50)
                    
                    # Să verificăm dacă codul conține main()
                    if 'main()' in test_code:
                        print("✅ Codul conține main()")
                    else:
                        print("❌ Codul NU conține main()")
                        
                    # Să verificăm dacă codul se compilează local
                    import tempfile
                    import subprocess
                    
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                        f.write(test_code)
                        temp_file = f.name
                    
                    try:
                        result = subprocess.run(['g++', '-o', temp_file.replace('.cpp', ''), temp_file], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            print("✅ Codul se compilează local cu g++")
                        else:
                            print("❌ Eroare compilare locală:")
                            print(result.stderr)
                    except Exception as e:
                        print(f"❌ Eroare la compilarea locală: {e}")
                    finally:
                        import os
                        try:
                            os.unlink(temp_file)
                            os.unlink(temp_file.replace('.cpp', ''))
                        except:
                            pass
                else:
                    print("❌ Nu s-a putut genera codul de test")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Eroare la testare: {e}")

if __name__ == "__main__":
    test_debug_compilation() 