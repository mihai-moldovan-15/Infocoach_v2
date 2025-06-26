from scraper import PbinfoScraper

def test_factorialf():
    scraper = PbinfoScraper()
    problem = scraper.extract_problem_data(896)
    
    if problem:
        print("✅ Problema FactorialF extrasă cu succes!")
        categories_str = ' '.join(f'[{cat}]' for cat in problem.get('categories', []))
        tags_str = ' '.join(f'[{tag}]' for tag in problem.get('tags', []))
        print(f"Nume: {problem['name']} {categories_str} {tags_str}")
        print(f"Clasa: {problem['grade']}")
        print(f"Categorie: {problem['category']}")
        print(f"Dificultate: {problem['difficulty']}")
        print(f"Limită timp: {problem['time_limit']}")
        print(f"Limită memorie: {problem['memory_limit']}")
        print("\nCerința:")
        print(problem['statement'])
        print("\nRestricții:")
        print(problem['constraints'])
        print("\nExemplu:")
        print(f"Input: {problem['example_input']}")
        print(f"Output: {problem['example_output']}")
        
        # Salvează în baza de date
        if scraper.save_problem(problem):
            print("\n✅ Problema salvată în baza de date!")
        else:
            print("\n❌ Eroare la salvarea în baza de date!")
    else:
        print("❌ Nu s-a putut extrage problema FactorialF")

if __name__ == "__main__":
    test_factorialf() 