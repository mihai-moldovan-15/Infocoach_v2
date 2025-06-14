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

            soup = BeautifulSoup(response.text, 'html.parser')

            # Verificare 404 sau pagină lipsă
            if soup.title and "Eroare" in soup.title.text:
                logging.warning(f"Problem {problem_id} not found (404 page)")
                return None

            # Salvare HTML pentru debugging
            with open(f'debug_{problem_id}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)

            # Nume problemă
            name_tag = soup.find('h1', class_='text-primary')
            name = self.clean_text(name_tag.text) if name_tag else ""

            logging.info(f"Problem name extracted: {name}")

            # Inițializare câmpuri
            intro = ""
            cerinta = ""
            input_desc = ""
            output_desc = ""
            constraints = ""
            example_input = ""
            example_output = ""

            problem_content = soup.find('article', id='enunt')
            if problem_content:
                current_section = None
                found_intro = False
                for tag in problem_content.find_all(['h1', 'p', 'pre']):
                    text = self.clean_text(tag.text)
                    text_lower = text.lower()

                    if tag.name == 'h1':
                        if "cerin" in text_lower:
                            current_section = "cerinta"
                        elif "date de intrare" in text_lower:
                            current_section = "input"
                        elif "date de ieșire" in text_lower or "date de iesire" in text_lower:
                            current_section = "output"
                        elif "restric" in text_lower:
                            current_section = "constraints"
                        elif "exemplu" in text_lower:
                            current_section = "example"
                        else:
                            current_section = None
                    elif tag.name == 'p':
                        if not found_intro:
                            intro = text
                            found_intro = True
                        elif current_section == "cerinta":
                            cerinta += text + "\n"
                        elif current_section == "input":
                            input_desc += text + "\n"
                        elif current_section == "output":
                            output_desc += text + "\n"
                        elif current_section == "constraints":
                            constraints += text + "\n"
                    elif tag.name == 'pre':
                        if current_section == "example":
                            # Heuristic: primul pre e input, al doilea e output
                            if not example_input:
                                example_input = text
                            else:
                                example_output = text

            # Statement = enunt + cerinta
            statement = intro.strip()
            if cerinta.strip():
                statement += "\n" + cerinta.strip()

            # Extragere metadate
            grade = None
            category = ""
            difficulty = ""

            info_table = soup.find('table', class_='table')
            if info_table:
                for row in info_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].text.lower()
                        value = self.clean_text(cells[1].text)

                        if 'clasa' in key:
                            try:
                                grade = int(re.search(r'\d+', value).group())
                            except:
                                pass
                        elif 'categorie' in key:
                            category = value
                        elif 'dificultate' in key:
                            difficulty = value

            logging.info(f"Grade: {grade}, Category: {category}, Difficulty: {difficulty}")

            return {
                'id': problem_id,
                'name': name,
                'statement': statement.strip(),
                'input_description': input_desc.strip(),
                'output_description': output_desc.strip(),
                'constraints': constraints.strip(),
                'example_input': example_input.strip(),
                'example_output': example_output.strip(),
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
            logging.info(f"Problem {problem_data['id']} saved successfully")
            return True
            
        except Exception as e:
            logging.error(f"Eroare la salvarea problemei {problem_data['id']}: {str(e)}")
            return False

if __name__ == "__main__":
    scraper = PbinfoScraper()
    # Adaugă problema 1 și 2
    for problem_id in [1, 2]:
        logging.info(f"Starting to scrape problem {problem_id}")
        problem_data = scraper.extract_problem_data(problem_id)
        if problem_data:
            logging.info(f"Successfully extracted data for problem {problem_id}")
            if scraper.save_problem(problem_data):
                logging.info(f"Problem {problem_id} was saved to database")
            else:
                logging.error(f"Failed to save problem {problem_id} to database")
        else:
            logging.error(f"Failed to extract data for problem {problem_id}") 