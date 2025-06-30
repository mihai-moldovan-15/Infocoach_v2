import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import logging
from datetime import datetime
import re
import unicodedata
import os

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
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
                example_input_name TEXT,
                example_output_name TEXT,
                grade INTEGER,
                category VARCHAR(100),
                difficulty VARCHAR(50),
                subcategories TEXT,
                time_limit TEXT,
                memory_limit TEXT,
                author TEXT,
                source TEXT,
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

    def normalize_text(self, text):
        # Normalizează diacriticele și spațiile
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '')

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
            example_input_name = ""
            example_output_name = ""

            problem_content = soup.find('article', id='enunt')
            if problem_content:
                # Verifică dacă este format nou (cu h1) sau format vechi
                h1_sections = problem_content.find_all('h1')
                if h1_sections:
                    # Format nou - folosește h1 pentru secțiuni
                    current_section = None
                    for tag in problem_content.find_all(['h1', 'p', 'pre', 'ul', 'li']):
                        text = self.clean_text(tag.text)
                        text_norm = self.normalize_text(text)
                        
                        if tag.name == 'h1':
                            if "cerin" in text_norm:
                                current_section = "cerinta"
                            elif "datedeintrare" in text_norm:
                                current_section = "input"
                            elif "datedeiesire" in text_norm:
                                current_section = "output"
                            elif "restrict" in text_norm or "preciz" in text_norm:
                                current_section = "constraints"
                            elif "exemplu" in text_norm:
                                current_section = "example"
                            elif "important" in text_norm:
                                current_section = "important"
                            else:
                                current_section = None
                        elif tag.name in ['p', 'pre']:
                            if current_section == "cerinta":
                                cerinta += text + "\n"
                            elif current_section == "input":
                                input_desc += text + "\n"
                            elif current_section == "output":
                                output_desc += text + "\n"
                            elif current_section == "constraints":
                                constraints += text + "\n"
                            elif current_section == "example":
                                if tag.name == 'pre':
                                    example_input = text
                                else:
                                    # Pentru exemple simple, folosește ca input și output
                                    example_input = text
                                    example_output = text
                            elif current_section == "important":
                                # Adaugă la cerință sau restricții
                                if not cerinta.strip():
                                    cerinta += text + "\n"
                                else:
                                    constraints += text + "\n"
                        elif tag.name == 'ul' and current_section == "constraints":
                            for li in tag.find_all('li'):
                                constraints += self.clean_text(li.text) + "\n"
                        elif tag.name == 'ul' and current_section == "input":
                            for li in tag.find_all('li'):
                                input_desc += self.clean_text(li.text) + "\n"
                        elif tag.name == 'ul' and current_section == "output":
                            for li in tag.find_all('li'):
                                output_desc += self.clean_text(li.text) + "\n"
                        elif tag.name == 'li' and current_section == "constraints":
                            constraints += self.clean_text(tag.text) + "\n"
                        elif tag.name == 'li' and current_section == "input":
                            input_desc += self.clean_text(tag.text) + "\n"
                        elif tag.name == 'li' and current_section == "output":
                            output_desc += self.clean_text(tag.text) + "\n"
                else:
                    # Format vechi - folosește logica robustă pentru orice tag după Intrare/Ieșire
                    in_example_input = False
                    in_example_output = False
                    for tag in problem_content.find_all(['h1', 'p', 'pre', 'span', 'b', 'div', 'code']):
                        text = self.clean_text(tag.text).lower()
                        if text == 'intrare':
                            in_example_input = True
                            in_example_output = False
                            continue
                        if text == 'ieșire' or text == 'iesire':
                            in_example_output = True
                            in_example_input = False
                            continue
                        if in_example_input and tag.text.strip():
                            example_input = tag.text.strip()
                            in_example_input = False
                        elif in_example_output and tag.text.strip():
                            example_output = tag.text.strip()
                            in_example_output = False

            # Fallback la "consola" dacă nu există nume de fișier
            if not example_input_name:
                example_input_name = "consola"
            if not example_output_name:
                example_output_name = "consola"

            # Statement = enunt + cerinta
            statement = intro.strip()
            if cerinta.strip():
                statement += "\n" + cerinta.strip()

            # Extragere metadate
            grade = None
            category = ""
            difficulty = ""
            time_limit = ''
            memory_limit = ''

            info_table = soup.find('table', class_='table')
            if info_table:
                rows = info_table.find_all('tr')
                if len(rows) >= 2:
                    cells = rows[1].find_all('td')
                    if len(cells) >= 8:
                        # Indexuri: 0=autor, 1=clasa, 2=input/output, 3=limită timp, 4=limită memorie, 5=sursa, 6=autor, 7=dificultate
                        try:
                            grade = int(re.search(r'\d+', cells[1].text).group())
                        except:
                            grade = None
                        time_limit = self.clean_text(cells[3].text)
                        memory_limit = self.clean_text(cells[4].text)
                        difficulty = self.clean_text(cells[7].text)
                        # category și altele pot fi extrase din breadcrumb sau altă logică

            # Extragere categorii din breadcrumb (fără clasa)
            categories = []
            breadcrumb = soup.find('ol', class_='breadcrumb')
            if breadcrumb:
                breadcrumb_items = breadcrumb.find_all('li', class_='breadcrumb-item')
                # Sar primul (clasa), restul sunt categorii
                for item in breadcrumb_items[1:]:
                    cat_text = self.clean_text(item.text)
                    if cat_text and cat_text != name:
                        categories.append(cat_text)

            # Extragere taguri (etichete)
            tags = []
            tag_container = soup.find('span', id='container-etichete')
            if tag_container:
                tag_links = tag_container.find_all('a', class_='badge')
                for tag_link in tag_links:
                    tag_text = self.clean_text(tag_link.text)
                    if tag_text:
                        tags.append(tag_text)

            logging.info(f"Grade: {grade}, Category: {category}, Difficulty: {difficulty}, Tags: {tags}, Categories: {categories}")

            return {
                'id': problem_id,
                'name': name,
                'statement': statement.strip(),
                'input_description': input_desc.strip(),
                'output_description': output_desc.strip(),
                'constraints': constraints.strip(),
                'example_input': example_input.strip(),
                'example_output': example_output.strip(),
                'example_input_name': example_input_name.strip(),
                'example_output_name': example_output_name.strip(),
                'grade': grade,
                'category': category,
                'difficulty': difficulty,
                'tags': tags,
                'categories': categories,
                'subcategories': '',
                'time_limit': time_limit,
                'memory_limit': memory_limit,
                'author': '',
                'source': '',
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
                constraints, example_input, example_output, example_input_name, example_output_name,
                grade, category, difficulty, subcategories, time_limit, memory_limit, author, source, last_updated, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                problem_data['id'],
                problem_data['name'],
                problem_data['statement'],
                problem_data['input_description'],
                problem_data['output_description'],
                problem_data['constraints'],
                problem_data['example_input'],
                problem_data['example_output'],
                problem_data['example_input_name'],
                problem_data['example_output_name'],
                problem_data['grade'],
                problem_data['category'],
                problem_data['difficulty'],
                problem_data['subcategories'],
                problem_data['time_limit'],
                problem_data['memory_limit'],
                problem_data['author'],
                problem_data['source'],
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

    def scrape_pbinfo(self):
        """Scrape primele 25 probleme de pe pbinfo.ro și le adaugă în baza de date. Salvează fișierele de debug în debug_files/."""
        debug_dir = 'debug_files'
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        base_url = "https://www.pbinfo.ro/probleme/"
        for problem_id in range(1, 26):
            url = f"{base_url}{problem_id}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Salvează fișierul de debug în folderul separat
                    with open(os.path.join(debug_dir, f'debug_{problem_id}.html'), 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    problem_data = self.extract_problem_data(problem_id)
                    if problem_data:
                        problem_data['id'] = problem_id
                        self.save_problem(problem_data)
                        print(f"Problema {problem_id} adăugată cu succes!")
                    else:
                        print(f"Nu s-au putut extrage datele pentru problema {problem_id}.")
                else:
                    print(f"Eroare la accesarea problemei {problem_id}: {response.status_code}")
            except Exception as e:
                print(f"Eroare la procesarea problemei {problem_id}: {e}")

if __name__ == "__main__":
    scraper = PbinfoScraper()
    scraper.scrape_pbinfo() 