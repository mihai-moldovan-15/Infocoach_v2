import json
import os

def convert_clasa_10_to_simple_format():
    """Convert class 10 JSON files from complex nested structure to simple array format"""
    
    clasa_10_dir = os.path.join('resources', 'resurse_pbinfo', 'clasa_10_json')
    output_dir = os.path.join('resources', 'resurse_pbinfo', 'clasa_10_json_simple')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all JSON files
    json_files = [f for f in os.listdir(clasa_10_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        file_path = os.path.join(clasa_10_dir, json_file)
        output_path = os.path.join(output_dir, json_file)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to simple array format
            fragments = []
            fragment_id = 1
            
            # Add main title as first fragment
            if 'title' in data:
                fragments.append({
                    "id": str(fragment_id),
                    "title": data['title'],
                    "content": data.get('description', ''),
                    "tags": data.get('tags', [])
                })
                fragment_id += 1
            
            # Process sections
            if 'sections' in data:
                for section in data['sections']:
                    # Add section title
                    if 'title' in section:
                        fragments.append({
                            "id": str(fragment_id),
                            "title": f"{data['title']} - {section['title']}",
                            "content": section.get('content', ''),
                            "tags": data.get('tags', [])
                        })
                        fragment_id += 1
                    
                    # Process subsections
                    if 'subsections' in section:
                        for subsection in section['subsections']:
                            fragments.append({
                                "id": str(fragment_id),
                                "title": f"{data['title']} - {section.get('title', '')} - {subsection.get('title', '')}",
                                "content": subsection.get('content', ''),
                                "tags": data.get('tags', [])
                            })
                            fragment_id += 1
            
            # Save converted file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(fragments, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Converted {json_file} ({len(fragments)} fragments)")
            
        except Exception as e:
            print(f"✗ Error converting {json_file}: {e}")
    
    print(f"\nConversion completed! Files saved in {output_dir}")

if __name__ == "__main__":
    convert_clasa_10_to_simple_format() 