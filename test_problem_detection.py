from app import detect_problem_type

def test_problem_detection():
    # Test cu problema FactorialF
    factorialf_statement = """
    Să se scrie o funcție C++ care să returneze pentru un număr natural n transmis ca parametru valoarea lui n!, adică 1•2•...•n.
    
    Restricții:
    - numele funcției va fi fact
    - funcția va avea un singur parametru, n
    - valoarea lui n! va fi returnată de către funcție
    - prin definiție, 0!=1
    - 0 ≤ n ≤ 12
    """
    
    problem_type = detect_problem_type(factorialf_statement)
    print(f"Problema FactorialF: {problem_type}")
    
    # Test cu o problemă care cere program complet
    complete_program_statement = """
    Scrie un program care citește un număr n și afișează toate numerele pare de la 1 la n.
    """
    
    problem_type2 = detect_problem_type(complete_program_statement)
    print(f"Problema program complet: {problem_type2}")
    
    # Test cu o problemă care cere o clasă
    class_problem_statement = """
    Implementează o clasă Calculator cu metodele add și multiply.
    """
    
    problem_type3 = detect_problem_type(class_problem_statement)
    print(f"Problema clasă: {problem_type3}")

if __name__ == "__main__":
    test_problem_detection() 