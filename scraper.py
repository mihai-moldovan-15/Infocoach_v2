import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import logging
from datetime import datetime
import re

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class PbinfoScraper:
    def __init__(self, db_path='problems.db'):
        self.db_path = db_path
        self.base_url = "https://www.pbinfo.ro/probleme"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.setup_database()

    def setup_database(self):
        """Creează baza de date și tabelul dacă nu există"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255),
                statement TEXT,
                input_description TEXT,
                output_description TEXT,
                constraints TEXT,
                example_input TEXT,
                example_output TEXT,
                grade INTEGER,
                category VARCHAR(100),
                difficulty VARCHAR(50),
                last_updated TIMESTAMP,
                status VARCHAR(20)
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Baza de date a fost inițializată")

    def clean_text(self, text):
        """Curăță textul de caractere nedorite"""
        if not text:
            return ""
        # Elimină spațiile multiple și newlines
        text = re.sub(r'\s+', ' ', text)
        # Elimină caracterele speciale
        text = text.replace('\xa0', ' ').strip()
        return text

    def extract_problem_data(self, problem_id):
        url = f"{self.base_url}/{problem_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            # Salvează HTML-ul pentru debug
            with open(f'debug_{problem_id}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            soup = BeautifulSoup(response.text, 'html.parser')

            name = self.clean_text(soup.find('h1').text) if soup.find('h1') else ""

            # Inițializează variabilele
            statement = ""
            input_desc = ""
            output_desc = ""
            constraints = ""
            example_input = ""
            example_output = ""

            # Parcurge toate cardurile
            for card in soup.find_all('div', class_='card'):
                header = card.find('div', class_='card-header')
                body = card.find('div', class_='card-body')
                if not header or not body:
                    continue
                header_text = header.text.strip().lower()
                body_text = self.clean_text(body.text)
                if 'enunțul problemei' in header_text:
                    statement = body_text
                elif 'date de intrare' in header_text:
                    input_desc = body_text
                elif 'date de ieșire' in header_text:
                    output_desc = body_text
                elif 'restricții' in header_text:
                    constraints = body_text
                elif 'exemplu' in header_text:
                    # Exemplul poate conține atât input cât și output
                    example_parts = body_text.split('Ieșire')
                    if len(example_parts) > 1:
                        example_input = example_parts[0].replace('Intrare', '').strip()
                        example_output = example_parts[1].strip()
                    else:
                        example_input = body_text

            # Extragem clasa, categoria și dificultatea (dacă există)
            grade = None
            category = ""
            difficulty = ""
            info_div = soup.find('div', class_='panel-info')
            if info_div:
                for span in info_div.find_all('span'):
                    text = span.text.lower()
                    if 'clasa' in text:
                        try:
                            grade = int(re.search(r'\d+', text).group())
                        except:
                            pass
                    elif 'categorie' in text:
                        category = self.clean_text(span.text.replace('Categorie:', ''))
                    elif 'dificultate' in text:
                        difficulty = self.clean_text(span.text.replace('Dificultate:', ''))

            return {
                'id': problem_id,
                'name': name,
                'statement': statement,
                'input_description': input_desc,
                'output_description': output_desc,
                'constraints': constraints,
                'example_input': example_input,
                'example_output': example_output,
                'grade': grade,
                'category': category,
                'difficulty': difficulty,
                'last_updated': datetime.now().isoformat(),
                'status': 'active'
            }
        except Exception as e:
            logging.error(f'Eroare la extragerea problemei {problem_id}: {str(e)}')
            return None

    def save_problem(self, problem_data):
        """Salvează problema în baza de date"""
        if not problem_data:
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO problems 
                (id, name, statement, input_description, output_description, 
                constraints, example_input, example_output, grade, category, 
                difficulty, last_updated, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                problem_data['id'],
                problem_data['name'],
                problem_data['statement'],
                problem_data['input_description'],
                problem_data['output_description'],
                problem_data['constraints'],
                problem_data['example_input'],
                problem_data['example_output'],
                problem_data['grade'],
                problem_data['category'],
                problem_data['difficulty'],
                problem_data['last_updated'],
                problem_data['status']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Eroare la salvarea problemei {problem_data['id']}: {str(e)}")
            return False

    def scrape_range(self, start_id, end_id):
        """Extrage problemele dintr-un interval de ID-uri"""
        for problem_id in range(start_id, end_id + 1):
            logging.info(f"Procesez problema {problem_id}")
            
            problem_data = self.extract_problem_data(problem_id)
            if problem_data:
                if self.save_problem(problem_data):
                    logging.info(f"Problema {problem_id} a fost salvată cu succes")
                else:
                    logging.error(f"Nu s-a putut salva problema {problem_id}")
            
            # Așteptăm 1 secundă între cereri pentru a nu supraîncărca serverul
            time.sleep(1)

def main():
    scraper = PbinfoScraper()
    
    # Poți ajusta intervalul de ID-uri după necesități
    start_id = 1
    end_id = 100  # Începem cu primele 100 de probleme pentru test
    
    logging.info(f"Încep extragerea problemelor de la {start_id} până la {end_id}")
    scraper.scrape_range(start_id, end_id)
    logging.info("Extragerea s-a încheiat")

if __name__ == "__main__":
    scraper = PbinfoScraper()
    data = scraper.extract_problem_data(3983)  # Poți schimba 3983 cu orice ID vrei să testezi
    print(data)
    main() 