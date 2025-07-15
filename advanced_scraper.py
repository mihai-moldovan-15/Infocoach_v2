import requests
from bs4 import BeautifulSoup
import sqlite3
import logging
import os
import re
from datetime import datetime
import json

# Listă de probleme speciale care vor fi adăugate manual
SPECIAL_PROBLEM_IDS = [910]  # ex: [910, 1234]

class AdvancedPbinfoScraper:
    def __init__(self, db_path='problems.db'):
        self.db_path = db_path
        self.base_url = "https://www.pbinfo.ro/probleme"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.setup_database()
        self.setup_logging()
        
    def setup_logging(self):
        """Configurează logging-ul"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('advanced_scraper.log'),
                logging.StreamHandler()
            ]
        )
    
    def setup_database(self):
        """Creează baza de date cu schema îmbunătățită"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                statement TEXT,
                input_description TEXT,
                output_description TEXT,
                constraints TEXT,
                example_input TEXT,
                example_output TEXT,
                example_input_name TEXT,
                example_output_name TEXT,
                grade INTEGER,
                category TEXT,
                difficulty TEXT,
                tags TEXT,
                categories TEXT,
                subcategories TEXT,
                time_limit TEXT,
                memory_limit TEXT,
                author TEXT,
                source TEXT,
                last_updated TEXT,
                status TEXT DEFAULT 'active',
                problem_type TEXT DEFAULT 'complete',
                has_images BOOLEAN DEFAULT 0,
                image_count INTEGER DEFAULT 0,
                images TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def clean_text(self, text):
        """Curăță textul de caractere nedorite"""
        if not text:
            return ""
        # Elimină caracterele de control și normalizează spațiile
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def normalize_text(self, text):
        """Normalizează textul pentru comparații"""
        if not text:
            return ""
        # Elimină diacriticele și normalizează spațiile
        text = re.sub(r'\s+', ' ', text.lower().strip())
        return text
    
    def detect_problem_type(self, content):
        """
        Detectează automat tipul de problemă bazat pe conținut și structură
        Returns: 'complete', 'subprogram', sau 'unknown'
        """
        if not content:
            return 'unknown'
        
        # Analizează textul pentru cuvinte cheie
        text = content.get_text().lower()
        
        # Cuvinte cheie pentru subprograme
        subprogram_keywords = [
            'scrie o funcție', 'scrie funcția', 'implementează o funcție', 'implementează funcția',
            'defineste o funcție', 'defineste funcția', 'să se scrie o funcție', 'să se scrie funcția',
            'să se implementeze o funcție', 'să se implementeze funcția', 'să se definească o funcție',
            'să se definească funcția', 'funcție', 'funcția', 'subprogram', 'subprogramul'
        ]
        
        # Cuvinte cheie pentru programe complete
        complete_keywords = [
            'scrie un program', 'scrie programul', 'implementează un program', 'implementează programul',
            'să se scrie un program', 'să se scrie programul', 'să se implementeze un program',
            'să se implementeze programul', 'programul va citi', 'programul va afișa', 'programul va scrie',
            'program', 'main', 'citeste', 'afiseaza', 'afișează'
        ]
        
        # Verifică cuvinte cheie
        subprogram_score = sum(1 for keyword in subprogram_keywords if keyword in text)
        complete_score = sum(1 for keyword in complete_keywords if keyword in text)
        
        # Analizează structura HTML
        h1_sections = content.find_all('h1')
        section_texts = [self.normalize_text(section.text) for section in h1_sections]
        
        # Verifică dacă există secțiuni specifice
        has_cerinta = any('cerin' in text for text in section_texts)
        has_date_intrare = any('date' in text and 'intrare' in text for text in section_texts)
        has_date_iesire = any('date' in text and 'iesire' in text for text in section_texts)
        
        # Logica de decizie
        if subprogram_score > complete_score:
            return 'subprogram'
        elif complete_score > subprogram_score:
            return 'complete'
        elif has_cerinta and has_date_intrare and has_date_iesire:
            # Structură completă - probabil program complet
            return 'complete'
        else:
            return 'unknown'
    
    def extract_images(self, content):
        """Extrage imaginile din conținut, excludând cele decorative"""
        images = []
        if not content:
            return images
        
        for img in content.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            if not self.is_decorative_image(src, alt):
                images.append({
                    'src': src,
                    'alt': alt,
                    'class': img.get('class', [])
                })
        
        return images
    
    def is_decorative_image(self, src, alt):
        """Verifică dacă o imagine este decorativă"""
        if not src:
            return True
            
        decorative_patterns = [
            'logo', 'icon', 'avatar', 'profile', 'user', 'menu', 'button',
            'header', 'footer', 'banner', 'advertisement', 'ad',
            'social', 'facebook', 'twitter', 'instagram', 'youtube',
            'play', 'pause', 'next', 'prev', 'close', 'search',
            'home', 'back', 'forward', 'refresh', 'download', 'upload',
            'star', 'heart', 'like', 'share', 'comment', 'edit', 'delete',
            'settings', 'config', 'gear', 'cog', 'wrench', 'tools',
            'notification', 'bell', 'alert', 'warning', 'error', 'success',
            'check', 'tick', 'cross', 'plus', 'minus', 'arrow', 'chevron'
        ]
        
        src_lower = src.lower()
        alt_lower = alt.lower()
        
        for pattern in decorative_patterns:
            if pattern in src_lower or pattern in alt_lower:
                return True
        
        if '16x16' in src_lower or '32x32' in src_lower or '48x48' in src_lower:
            return True
        
        if 'background' in src_lower or 'bg' in src_lower:
            return True
        
        return False
    
    def extract_section(self, problem_content, section_name, stop_headings):
        blocks = []
        in_section = False
        for tag in problem_content.children:
            if getattr(tag, 'name', None) == 'h1':
                heading = tag.get_text(separator=" ").strip().lower()
                if section_name in heading:
                    in_section = True
                    continue
                if in_section and any(stop in heading for stop in stop_headings):
                    break
            elif in_section and getattr(tag, 'get_text', None):
                text = tag.get_text(separator=" ").strip()
                if text:
                    blocks.append(text)
        return "\n\n".join(blocks).strip()
    
    def extract_examples_from_article(self, article):
        import re
        example_input = ''
        example_output = ''
        example_input_name = ''
        example_output_name = ''
        found_example = False
        found_input = False
        found_output = False
        input_lines = []
        output_lines = []
        input_name = ''
        output_name = ''
        current = None
        explanation_lines = []
        after_output = False
        for tag in article.find_all(['h1','h2','h3','b','strong','span','p','pre','div']):
            text = tag.get_text(separator='\n').strip()
            text_norm = self.normalize_text(text)
            if re.match(r'.+\.in$', text):
                input_name = text
                current = 'input'
                found_example = True
                after_output = False
                continue
            if re.match(r'.+\.out$', text):
                output_name = text
                current = 'output'
                found_example = True
                after_output = False
                continue
            if text_norm in ['exemplu','exemplu:','exemple','exemple:']:
                found_example = True
                current = None
                after_output = False
                continue
            if text_norm in ['intrare','intrare:']:
                found_input = True
                found_output = False
                current = 'input'
                after_output = False
                continue
            if text_norm in ['ieșire','iesire','ieșire:','iesire:']:
                found_output = True
                found_input = False
                current = 'output'
                after_output = False
                continue
            if found_example and current == 'input' and text and not re.match(r'.+\.in$', text):
                input_lines.append(text)
            if found_example and current == 'output' and text and not re.match(r'.+\.out$', text):
                output_lines.append(text)
                after_output = True
                continue
            # După output, dacă mai există text și nu e heading nou, colectează ca explicație
            if found_example and after_output and not re.match(r'.+\.out$', text) and not text_norm in ['exemplu','exemplu:','exemple','exemple:','intrare','intrare:','ieșire','iesire','ieșire:','iesire:'] and text:
                explanation_lines.append(text)
        if input_name:
            example_input_name = input_name
        if output_name:
            example_output_name = output_name
        example_input = '\n'.join(input_lines).strip()
        example_output = '\n'.join(output_lines).strip()
        if not example_input and not example_output:
            pre_blocks = article.find_all('pre')
            if len(pre_blocks) == 1:
                block = pre_blocks[0].get_text(separator='\n')
                if 'Intrare' in block and ('Ieșire' in block or 'Iesire' in block):
                    lines = [l.strip() for l in block.splitlines() if l.strip()]
                    in_input = False
                    in_output = False
                    for line in lines:
                        if line.lower() == 'intrare':
                            in_input = True
                            in_output = False
                            continue
                        if line.lower() in ['ieșire','iesire']:
                            in_input = False
                            in_output = True
                            continue
                        if in_input:
                            input_lines.append(line)
                        elif in_output:
                            output_lines.append(line)
                    example_input = '\n'.join(input_lines).strip()
                    example_output = '\n'.join(output_lines).strip()
        if not example_input and input_lines:
            example_input = '\n'.join(input_lines).strip()
        if not example_output and output_lines:
            example_output = '\n'.join(output_lines).strip()
        example_explanation = '\n'.join(explanation_lines).strip()
        return example_input, example_output, example_input_name or 'consola', example_output_name or 'consola', example_explanation
    
    def extract_example_section(self, article):
        example_lines = []
        in_example = False
        for tag in article.children:
            if getattr(tag, 'name', None) == 'h1' and 'exemplu' in tag.get_text(separator=' ').lower():
                in_example = True
                continue
            if in_example and getattr(tag, 'name', None) == 'h1':
                break  # următorul heading, se oprește
            if in_example and getattr(tag, 'get_text', None):
                text = tag.get_text(separator=' ').strip()
                if text:
                    example_lines.append(text)
        return '\n'.join(example_lines).strip()
    
    def extract_complete_problem(self, soup, problem_id):
        """Extrage datele pentru o problemă cu program complet"""
        problem_data = {
            'id': problem_id,
            'name': '',
            'statement': '',
            'input_description': '',
            'output_description': '',
            'constraints': '',
            'example_input': '',
            'example_output': '',
            'example_input_name': 'consola',
            'example_output_name': 'consola',
            'example_explanation': '',
            'problem_type': 'complete',
            'has_images': False,
            'image_count': 0,
            'images': []
        }
        # Titlu
        title_tag = soup.find('h1', class_='text-primary')
        if title_tag:
            problem_data['name'] = self.clean_text(title_tag.text)
        # Conținutul problemei
        problem_content = soup.find('article', id='enunt')
        if not problem_content:
            return None
        # Verifică imagini
        images = self.extract_images(problem_content)
        if images:
            problem_data['has_images'] = True
            problem_data['image_count'] = len(images)
            problem_data['images'] = json.dumps(images)
            return problem_data
        # --- Enunț până la primul heading de date/restricții/exemplu, fără heading-ul Cerința ---
        intro_text = ""
        for tag in problem_content.children:
            if getattr(tag, 'name', None) == 'h1':
                heading = tag.get_text(separator=" ").strip().lower()
                if any(keyword in heading for keyword in ['date de intrare', 'date de ieșire', 'date de iesire', 'restric', 'exemplu']):
                    break
                if 'cerin' in heading:
                    continue
            if getattr(tag, 'get_text', None):
                text = tag.get_text(separator=" ").strip()
                if text:
                    intro_text += text + "\n\n"
        statement = re.sub(r'\n{3,}', '\n\n', intro_text.strip())
        # --- extragere robustă pentru secțiuni ---
        input_desc = self.extract_section(
            problem_content,
            'date de intrare',
            ['date de ieșire', 'date de iesire', 'restric', 'exemplu']
        )
        output_desc = self.extract_section(
            problem_content,
            'date de ieșire',
            ['restric', 'exemplu']
        )
        constraints = self.extract_section(
            problem_content,
            'restric',
            ['exemplu']
        )
        # --- extragere exemplu robustă: DOAR extract_examples_from_article ---
        example_input, example_output, example_input_name, example_output_name, example_explanation = self.extract_examples_from_article(problem_content)
        # Elimină exemplul din restricții dacă există
        constraints_cleaned = constraints.replace(example_input, '').strip()
        problem_data['statement'] = statement.strip()
        problem_data['constraints'] = self.clean_constraints(constraints_cleaned)
        problem_data['input_description'] = input_desc
        problem_data['output_description'] = output_desc
        problem_data['example_input'] = example_input
        problem_data['example_output'] = example_output
        problem_data['example_input_name'] = example_input_name
        problem_data['example_output_name'] = example_output_name
        problem_data['example_explanation'] = example_explanation
        return problem_data
    
    def extract_subprogram_problem(self, soup, problem_id):
        """Extrage datele pentru o problemă cu subprogram"""
        problem_data = {
            'id': problem_id,
            'name': '',
            'statement': '',
            'input_description': '',
            'output_description': '',
            'constraints': '',
            'example_input': '',
            'example_output': '',
            'example_input_name': 'consola',
            'example_output_name': 'consola',
            'problem_type': 'subprogram',
            'has_images': False,
            'image_count': 0,
            'images': []
        }
        title_tag = soup.find('h1', class_='text-primary')
        if title_tag:
            problem_data['name'] = self.clean_text(title_tag.text)
        problem_content = soup.find('article', id='enunt')
        if not problem_content:
            return None
        images = self.extract_images(problem_content)
        if images:
            problem_data['has_images'] = True
            problem_data['image_count'] = len(images)
            problem_data['images'] = json.dumps(images)
            return problem_data
        # --- NOU: extragere robustă pentru subprograme ---
        found_cerinta = False
        found_restrictii = False
        statement = ''
        constraints = ''
        for tag in problem_content.children:
            if getattr(tag, 'name', None) == 'h1' and 'cerin' in tag.get_text(separator=" ").strip().lower():
                found_cerinta = True
                continue
            if getattr(tag, 'name', None) == 'h1' and any(x in tag.get_text(separator=" ").strip().lower() for x in ['exemplu', 'important', 'preciz', 'restrict']):
                found_restrictii = True
                continue
            if getattr(tag, 'get_text', None):
                text = tag.get_text(separator=" ").strip()
                if not found_cerinta or not text:
                    continue
                if not found_restrictii and not statement:
                    statement = text
                elif found_restrictii or (statement and text):
                    constraints += text + "\n"
        problem_data['statement'] = statement.strip()
        problem_data['constraints'] = self.clean_constraints(constraints.strip())
        problem_data['input_description'] = ''
        problem_data['output_description'] = ''
        # --- extragere exemplu dacă există heading ---
        example_input = self.extract_example_section(problem_content)
        # Elimină exemplul din restricții dacă există
        constraints_cleaned = constraints.replace(example_input, '').strip()
        problem_data['statement'] = statement.strip()
        problem_data['constraints'] = self.clean_constraints(constraints_cleaned)
        problem_data['input_description'] = ''
        problem_data['output_description'] = ''
        problem_data['example_input'] = example_input
        problem_data['example_output'] = ''
        problem_data['example_input_name'] = 'consola'
        problem_data['example_output_name'] = 'consola'
        return problem_data
    
    def extract_metadata(self, soup):
        """Extrage metadatele problemei"""
        metadata = {
            'grade': None,
            'difficulty': '',
            'time_limit': '',
            'memory_limit': '',
            'categories': [],
            'tags': [],
            'subcategories': []
        }
        # Tabelul de informații
        info_table = soup.find('table', class_='table')
        if info_table:
            rows = info_table.find_all('tr')
            if len(rows) >= 2:
                cells = rows[1].find_all('td')
                if len(cells) >= 8:
                    try:
                        grade_match = re.search(r'\d+', cells[1].text)
                        if grade_match:
                            metadata['grade'] = int(grade_match.group())
                    except:
                        pass
                    metadata['time_limit'] = self.clean_text(cells[3].text)
                    metadata['memory_limit'] = self.clean_text(cells[4].text)
                    metadata['difficulty'] = self.clean_text(cells[7].text)
        # Breadcrumb pentru categorii
        breadcrumb = soup.find('ol', class_='breadcrumb')
        if breadcrumb:
            items = breadcrumb.find_all('li', class_='breadcrumb-item')
            categories = [self.clean_text(item.text) for item in items[1:] if item.text.strip()]
            # Păstrează doar prima categorie dacă există
            if categories:
                metadata['categories'] = [categories[0]]
                # Subcategoriile sunt restul, fără titlul problemei
                subcats = categories[1:]
                # Elimină subcategoria identică cu titlul problemei (case-insensitive)
                title = ''
                title_tag = soup.find('h1', class_='text-primary')
                if title_tag:
                    title = self.clean_text(title_tag.text).lower()
                subcats = [c for c in subcats if c.lower() != title]
                metadata['subcategories'] = subcats
            else:
                metadata['categories'] = []
                metadata['subcategories'] = []
        # Taguri
        tag_container = soup.find('span', id='container-etichete')
        if tag_container:
            tags = tag_container.find_all('a', class_='badge')
            metadata['tags'] = [self.clean_text(tag.text) for tag in tags if tag.text.strip()]
        return metadata
    
    def extract_problem_data(self, problem_id):
        """Extrage datele unei probleme cu detecție automată a tipului"""
        url = f"{self.base_url}/{problem_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logging.warning(f"Problem {problem_id} not found (status: {response.status_code})")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verificare 404 sau pagină lipsă
            if soup.title and "Eroare" in soup.title.text:
                logging.warning(f"Problem {problem_id} not found (404 page)")
                return None
            
            # Conținutul problemei
            problem_content = soup.find('article', id='enunt')
            if not problem_content:
                logging.warning(f"Problem {problem_id} has no content")
                return None
            
            # Detectează tipul problemei
            problem_type = self.detect_problem_type(problem_content)
            logging.info(f"Problem {problem_id} detected as type: {problem_type}")
            
            # Extrage datele în funcție de tip
            if problem_type == 'complete':
                problem_data = self.extract_complete_problem(soup, problem_id)
            elif problem_type == 'subprogram':
                problem_data = self.extract_subprogram_problem(soup, problem_id)
            else:
                # Pentru tipuri necunoscute, încearcă ca program complet
                problem_data = self.extract_complete_problem(soup, problem_id)
                problem_data['problem_type'] = 'unknown'
            
            if not problem_data:
                return None
            
            # Adaugă metadatele
            metadata = self.extract_metadata(soup)
            problem_data.update({
                'grade': metadata['grade'],
                'category': '',
                'difficulty': metadata['difficulty'],
                'time_limit': metadata['time_limit'],
                'memory_limit': metadata['memory_limit'],
                'tags': json.dumps(metadata['tags']),
                'categories': json.dumps(metadata['categories']),
                'subcategories': json.dumps(metadata['subcategories']),
                'author': '',
                'source': '',
                'last_updated': datetime.now().isoformat(),
                'status': 'active'
            })
            
            return problem_data
            
        except Exception as e:
            logging.error(f'Error extracting problem {problem_id}: {str(e)}')
            return None
    
    def save_problem(self, problem_data):
        """Salvează problema în baza de date"""
        if not problem_data:
            return False
        
        # Asigură-te că images, tags și categories sunt stringuri JSON
        for key in ['images', 'tags', 'categories', 'subcategories']:
            if isinstance(problem_data.get(key), list):
                problem_data[key] = json.dumps(problem_data[key])
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO problems 
                (id, name, statement, input_description, output_description, 
                constraints, example_input, example_output, example_input_name, example_output_name,
                grade, category, difficulty, tags, categories, subcategories, time_limit, memory_limit, 
                author, source, last_updated, status, problem_type, has_images, image_count, images)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                problem_data['tags'],
                problem_data['categories'],
                problem_data['subcategories'],
                problem_data['time_limit'],
                problem_data['memory_limit'],
                problem_data['author'],
                problem_data['source'],
                problem_data['last_updated'],
                problem_data['status'],
                problem_data['problem_type'],
                problem_data['has_images'],
                problem_data['image_count'],
                problem_data['images']
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"Problem {problem_data['id']} saved successfully (type: {problem_data['problem_type']})")
            return True
            
        except Exception as e:
            logging.error(f"Error saving problem {problem_data['id']}: {str(e)}")
            return False
    
    def scrape_problem_list(self, problem_ids):
        debug_dir = 'debug_problems'
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        problems_with_images = []
        for problem_id in problem_ids:
            url = f"{self.base_url}/{problem_id}"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    problem_content = soup.find('article', id='enunt')
                    if problem_content:
                        images = self.extract_images(problem_content)
                        if images:
                            problems_with_images.append({
                                'id': problem_id,
                                'image_count': len(images),
                                'images': images
                            })
                            print(f"⚠️  Problema {problem_id} conține {len(images)} imagini - va fi pusă în lista manuală")
                            continue
                    problem_data = self.extract_problem_data(problem_id)
                    if problem_data:
                        if self.save_problem(problem_data):
                            with open(os.path.join(debug_dir, f'debug_{problem_id}.html'), 'w', encoding='utf-8') as f:
                                f.write(response.text)
                            print(f"✅ Problema {problem_id} ({problem_data['problem_type']}) salvată cu succes!")
                        else:
                            print(f"❌ Nu s-a putut salva problema {problem_id}")
                    else:
                        print(f"❌ Nu s-au putut extrage datele pentru problema {problem_id}")
                else:
                    print(f"❌ Eroare la accesarea problemei {problem_id}: {response.status_code}")
            except Exception as e:
                print(f"❌ Eroare la procesarea problemei {problem_id}: {e}")
        if problems_with_images:
            with open('problems_with_images.json', 'w', encoding='utf-8') as f:
                json.dump(problems_with_images, f, ensure_ascii=False, indent=2)
            print(f"\n📋 {len(problems_with_images)} probleme cu imagini salvate în problems_with_images.json")

    def clean_constraints(self, text):
        import re
        pattern = re.compile(
            r'solu(ţ|t)a propus(ă|a) va con(ţ|t)ine doar defini(ţ|t)ia func(ţ|t)iei cerute\.?( )*prezen(ţ|t)a (în|in) solu(ţ|t)ie a altor instruc(ţ|t)iuni poate duce erori de compilare sau de execu(ţ|t)ie care vor avea ca efect depunctarea solu(ţ|t)iei\.?',
            re.IGNORECASE
        )
        return pattern.sub('', text).strip()

if __name__ == "__main__":
    scraper = AdvancedPbinfoScraper()
    problem_ids = list(range(1, 1001))
    for pid in SPECIAL_PROBLEM_IDS:
        if pid not in problem_ids:
            problem_ids.append(pid)
    print("Probleme de procesat:", problem_ids)
    scraper.scrape_problem_list(problem_ids) 