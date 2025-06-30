import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

class ProblemAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def analyze_problem(self, problem_id, problem_type):
        """Analizează o problemă și extrage structura sa"""
        url = f"https://www.pbinfo.ro/probleme/{problem_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Eroare la accesarea problemei {problem_id}: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verifică dacă pagina conține imagini în conținutul problemei
            problem_content = soup.find('article', id='enunt')
            content_images = []
            
            if problem_content:
                # Caută imagini doar în conținutul problemei
                images = problem_content.find_all('img')
                for img in images:
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    # Exclude imagini decorative
                    if not self.is_decorative_image(src, alt):
                        content_images.append({
                            'src': src,
                            'alt': alt,
                            'class': img.get('class', [])
                        })
            
            has_content_images = len(content_images) > 0
            
            if has_content_images:
                print(f"⚠️  Problema {problem_id} conține imagini în conținut - va fi pusă în lista manuală")
                return {
                    'id': problem_id,
                    'type': problem_type,
                    'has_images': True,
                    'image_count': len(content_images),
                    'images': content_images
                }
            
            # Extrage structura problemei
            analysis = {
                'id': problem_id,
                'type': problem_type,
                'has_images': False,
                'url': url,
                'title': '',
                'structure': {},
                'html_structure': {},
                'content_patterns': {}
            }
            
            # Titlu
            title_tag = soup.find('h1', class_='text-primary')
            if title_tag:
                analysis['title'] = title_tag.text.strip()
            
            # Analizează structura HTML
            if problem_content:
                analysis['html_structure'] = self.analyze_html_structure(problem_content)
                analysis['structure'] = self.extract_content_structure(problem_content)
                analysis['content_patterns'] = self.analyze_content_patterns(problem_content)
            
            # Metadate
            analysis['metadata'] = self.extract_metadata(soup)
            
            return analysis
            
        except Exception as e:
            print(f"Eroare la analizarea problemei {problem_id}: {e}")
            return None
    
    def analyze_html_structure(self, content):
        """Analizează structura HTML a conținutului"""
        structure = {
            'sections': [],
            'tags_used': {},
            'hierarchy': []
        }
        
        # Analizează tag-urile folosite
        for tag in content.find_all():
            tag_name = tag.name
            if tag_name not in structure['tags_used']:
                structure['tags_used'][tag_name] = 0
            structure['tags_used'][tag_name] += 1
        
        # Analizează secțiunile (h1, h2, etc.)
        for heading in content.find_all(['h1', 'h2', 'h3', 'h4']):
            section = {
                'type': heading.name,
                'text': heading.text.strip(),
                'normalized_text': self.normalize_text(heading.text.strip().lower()),
                'has_content_after': bool(heading.find_next_sibling())
            }
            structure['sections'].append(section)
        
        return structure
    
    def extract_content_structure(self, content):
        """Extrage structura conținutului organizat pe categorii"""
        structure = {
            'enunt': '',
            'cerinta': '',
            'date_intrare': '',
            'date_iesire': '',
            'restrictii': '',
            'exemplu': '',
            'exemplu_intrare': '',
            'exemplu_iesire': '',
            'important': '',
            'limite': {}
        }
        
        # Logica de extragere bazată pe patternurile identificate
        current_section = None
        
        for tag in content.find_all(['h1', 'h2', 'h3', 'p', 'pre', 'ul', 'li', 'div']):
            text = tag.text.strip()
            if not text:
                continue
                
            normalized_text = self.normalize_text(text.lower())
            
            # Detectează secțiunea
            if tag.name in ['h1', 'h2', 'h3']:
                if 'cerin' in normalized_text:
                    current_section = 'cerinta'
                elif 'date' in normalized_text and 'intrare' in normalized_text:
                    current_section = 'date_intrare'
                elif 'date' in normalized_text and 'iesire' in normalized_text:
                    current_section = 'date_iesire'
                elif 'restrict' in normalized_text or 'preciz' in normalized_text:
                    current_section = 'restrictii'
                elif 'exemplu' in normalized_text:
                    current_section = 'exemplu'
                elif 'important' in normalized_text:
                    current_section = 'important'
                else:
                    current_section = None
            else:
                # Adaugă conținutul la secțiunea curentă
                if current_section and current_section in structure:
                    if tag.name == 'pre':
                        if current_section == 'exemplu':
                            if not structure['exemplu_intrare']:
                                structure['exemplu_intrare'] = text
                            else:
                                structure['exemplu_iesire'] = text
                        else:
                            structure[current_section] += text + '\n'
                    else:
                        structure[current_section] += text + '\n'
        
        return structure
    
    def analyze_content_patterns(self, content):
        """Analizează patternurile de conținut"""
        patterns = {
            'keywords': [],
            'code_blocks': [],
            'lists': [],
            'tables': []
        }
        
        # Cuvinte cheie
        all_text = content.get_text().lower()
        keywords = [
            'scrie', 'implementează', 'defineste', 'funcție', 'funcția', 'clasă', 'clasa',
            'program', 'main', 'citeste', 'afiseaza', 'afișează', 'consola', 'fisier',
            'intrare', 'iesire', 'ieșire', 'restrictii', 'precizari', 'exemplu'
        ]
        
        for keyword in keywords:
            if keyword in all_text:
                patterns['keywords'].append(keyword)
        
        # Blocuri de cod
        code_blocks = content.find_all('pre')
        patterns['code_blocks'] = [block.text.strip() for block in code_blocks]
        
        # Liste
        lists = content.find_all(['ul', 'ol'])
        patterns['lists'] = [lst.get_text().strip() for lst in lists]
        
        # Tabele
        tables = content.find_all('table')
        patterns['tables'] = [table.get_text().strip() for table in tables]
        
        return patterns
    
    def extract_metadata(self, soup):
        """Extrage metadatele problemei"""
        metadata = {
            'grade': None,
            'difficulty': '',
            'time_limit': '',
            'memory_limit': '',
            'categories': [],
            'tags': []
        }
        
        # Tabelul de informații
        info_table = soup.find('table', class_='table')
        if info_table:
            rows = info_table.find_all('tr')
            if len(rows) >= 2:
                cells = rows[1].find_all('td')
                if len(cells) >= 8:
                    try:
                        import re
                        grade_match = re.search(r'\d+', cells[1].text)
                        if grade_match:
                            metadata['grade'] = int(grade_match.group())
                    except:
                        pass
                    metadata['time_limit'] = cells[3].text.strip()
                    metadata['memory_limit'] = cells[4].text.strip()
                    metadata['difficulty'] = cells[7].text.strip()
        
        # Breadcrumb pentru categorii
        breadcrumb = soup.find('ol', class_='breadcrumb')
        if breadcrumb:
            items = breadcrumb.find_all('li', class_='breadcrumb-item')
            metadata['categories'] = [item.text.strip() for item in items[1:] if item.text.strip()]
        
        # Taguri
        tag_container = soup.find('span', id='container-etichete')
        if tag_container:
            tags = tag_container.find_all('a', class_='badge')
            metadata['tags'] = [tag.text.strip() for tag in tags if tag.text.strip()]
        
        return metadata
    
    def normalize_text(self, text):
        """Normalizează textul pentru comparații"""
        import re
        # Elimină diacriticele și normalizează spațiile
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def is_decorative_image(self, src, alt):
        """Verifică dacă o imagine este decorativă (logo, iconiță, etc.)"""
        if not src:
            return True
            
        # Exclude imagini decorative comune
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
        
        # Verifică dacă src sau alt conțin patternuri decorative
        for pattern in decorative_patterns:
            if pattern in src_lower or pattern in alt_lower:
                return True
        
        # Verifică dacă este o imagine foarte mică (probabil iconiță)
        if '16x16' in src_lower or '32x32' in src_lower or '48x48' in src_lower:
            return True
        
        # Verifică dacă este o imagine din CSS (background-image)
        if 'background' in src_lower or 'bg' in src_lower:
            return True
        
        return False
    
    def analyze_all_problems(self):
        """Analizează toate problemele furnizate"""
        problems = {
            'complete': [106, 2178, 207, 3521, 3387, 4576, 1024, 2893, 672],
            'subprogram': [4271, 3798, 40, 805, 895]
        }
        
        results = {
            'complete': [],
            'subprogram': [],
            'with_images': [],
            'analysis_summary': {}
        }
        
        print("🔍 Analizez problemele...")
        
        for problem_type, problem_ids in problems.items():
            print(f"\n📋 Analizez problemele de tip: {problem_type}")
            for problem_id in problem_ids:
                print(f"  - Analizez problema {problem_id}...")
                analysis = self.analyze_problem(problem_id, problem_type)
                
                if analysis:
                    if analysis.get('has_images'):
                        results['with_images'].append(analysis)
                    else:
                        results[problem_type].append(analysis)
        
        # Salvează rezultatele
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"problem_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Analiza completă salvată în {filename}")
        
        # Afișează un sumar
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results):
        """Afișează un sumar al analizei"""
        print("\n" + "="*60)
        print("📊 SUMAR ANALIZĂ PROBLEME")
        print("="*60)
        
        print(f"\n🔢 Probleme cu program complet: {len(results['complete'])}")
        print(f"🔧 Probleme cu subprograme: {len(results['subprogram'])}")
        print(f"🖼️  Probleme cu imagini (necesită procesare manuală): {len(results['with_images'])}")
        
        if results['with_images']:
            print(f"\n⚠️  Probleme cu imagini:")
            for problem in results['with_images']:
                print(f"   - ID: {problem['id']}, Tip: {problem['type']}, Imagini: {problem['image_count']}")
        
        # Analizează patternurile
        if results['complete'] and results['subprogram']:
            print(f"\n🔍 PATTERNURI IDENTIFICATE:")
            
            # Compară structura HTML
            complete_tags = set()
            subprogram_tags = set()
            
            for problem in results['complete']:
                complete_tags.update(problem['html_structure']['tags_used'].keys())
            
            for problem in results['subprogram']:
                subprogram_tags.update(problem['html_structure']['tags_used'].keys())
            
            print(f"   - Tag-uri comune: {complete_tags & subprogram_tags}")
            print(f"   - Tag-uri specifice programe complete: {complete_tags - subprogram_tags}")
            print(f"   - Tag-uri specifice subprograme: {subprogram_tags - complete_tags}")

if __name__ == "__main__":
    analyzer = ProblemAnalyzer()
    results = analyzer.analyze_all_problems() 