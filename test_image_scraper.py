#!/usr/bin/env python3
"""
Script de test pentru funcționalitatea de procesare a imaginilor
"""

from advanced_scraper import AdvancedPbinfoScraper
import json
import traceback

def test_image_processing():
    """Testează procesarea imaginilor pentru problema 3387"""
    scraper = AdvancedPbinfoScraper()
    
    # Testează cu problema 3387 care conține imagini
    problem_id = 3387
    print(f"🔄 Testez procesarea imaginilor pentru problema {problem_id}...")
    
    try:
        problem_data = scraper.extract_problem_data(problem_id)
        
        if problem_data:
            print(f"✅ Problema {problem_id} procesată cu succes!")
            print(f"📝 Nume: {problem_data['name']}")
            print(f"🖼️  Are imagini: {problem_data['has_images']}")
            print(f"📊 Număr imagini: {problem_data['image_count']}")
            
            if problem_data['has_images']:
                images = json.loads(problem_data['images'])
                print(f"📋 Imagini procesate:")
                for i, img in enumerate(images):
                    print(f"  {i+1}. {img['original_src']} -> {img['local_path']}")
            
            # Salvează în baza de date
            if scraper.save_problem(problem_data):
                print(f"💾 Problema salvată în baza de date!")
            else:
                print(f"❌ Eroare la salvarea în baza de date!")
        else:
            print(f"❌ Nu s-au putut extrage datele pentru problema {problem_id}")
    except Exception as e:
        print(f"❌ Eroare: {str(e)}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_image_processing() 