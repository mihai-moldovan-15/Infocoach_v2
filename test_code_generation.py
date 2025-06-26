from app import generate_test_code_for_subprogram

def test_code_generation():
    """Testează generarea codului de test pentru subprograme"""
    
    # Datele de test
    problem_statement = """
    Să se scrie o funcție C++ care să returneze pentru un număr natural n transmis ca parametru valoarea lui n!, adică 1•2•...•n.
    
    Restricții:
    - numele funcției va fi fact
    - funcția va avea un singur parametru, n
    - valoarea lui n! va fi returnată de către funcție
    - prin definiție, 0!=1
    - 0 ≤ n ≤ 12
    """
    
    user_code = """
int fact(int n) {
    if (n == 0) return 1;
    return n * fact(n - 1);
}
"""
    
    problem_id = 896
    
    print("🧪 Testez generarea codului de test...")
    
    try:
        test_code = generate_test_code_for_subprogram(problem_statement, user_code, problem_id)
        
        if test_code:
            print("✅ Codul de test a fost generat cu succes!")
            print("\n📝 Codul generat:")
            print("=" * 50)
            print(test_code)
            print("=" * 50)
            
            # Verifică dacă codul conține elementele necesare
            if '#include' in test_code and 'main()' in test_code and 'fact(' in test_code:
                print("✅ Codul conține toate elementele necesare!")
            else:
                print("⚠️ Codul pare să nu conțină toate elementele necesare")
                
        else:
            print("❌ Eroare la generarea codului de test")
            
    except Exception as e:
        print(f"❌ Eroare: {e}")

if __name__ == "__main__":
    test_code_generation() 