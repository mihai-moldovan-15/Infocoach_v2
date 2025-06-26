from app import generate_test_code_for_subprogram

def test_your_function():
    """Testează cu funcția exactă a utilizatorului"""
    
    # Funcția exactă a utilizatorului
    user_code = """int fact(int n, int p=1)
{
    for(int i=1;i<=n;i++)
        p*=i;
    return p;
}"""
    
    problem_statement = """
    Să se scrie o funcție C++ care să returneze pentru un număr natural n transmis ca parametru valoarea lui n!, adică 1•2•...•n.
    
    Restricții:
    - numele funcției va fi fact
    - funcția va avea un singur parametru, n
    - valoarea lui n! va fi returnată de către funcție
    - prin definiție, 0!=1
    - 0 ≤ n ≤ 12
    """
    
    problem_id = 896
    
    print("🧪 Testez cu funcția ta exactă...")
    print(f"Funcția ta: {user_code}")
    
    try:
        test_code = generate_test_code_for_subprogram(problem_statement, user_code, problem_id)
        
        if test_code:
            print("\n✅ Codul de test a fost generat cu succes!")
            print("\n📝 Codul generat:")
            print("=" * 60)
            print(test_code)
            print("=" * 60)
            
            # Verifică dacă codul conține funcția exactă a utilizatorului
            if 'int fact(int n, int p=1)' in test_code:
                print("✅ Codul conține funcția ta exactă!")
            else:
                print("⚠️ Codul nu conține funcția ta exactă")
                
            # Verifică dacă are main
            if 'main()' in test_code:
                print("✅ Codul conține main()")
            else:
                print("❌ Codul nu conține main()")
                
        else:
            print("❌ Eroare la generarea codului de test")
            
    except Exception as e:
        print(f"❌ Eroare: {e}")

if __name__ == "__main__":
    test_your_function() 