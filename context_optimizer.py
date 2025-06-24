import os
import json
import re

class ContextOptimizer:
    def __init__(self, json_folders):
        self.fragments = []
        self.load_fragments(json_folders)

    def load_fragments(self, json_folders):
        """
        Loads all text fragments from JSON files in the specified folders.
        Each fragment is stored with its source file path.
        """
        for folder in json_folders:
            if not os.path.isdir(folder):
                print(f"Warning: Directory not found - {folder}")
                continue
            
            for filename in os.listdir(folder):
                if filename.endswith('.json'):
                    filepath = os.path.join(folder, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # Handle array of objects structure
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict) and 'content' in item:
                                        content = item['content']
                                        if content.strip():
                                            self.fragments.append({
                                                'source': filepath,
                                                'content': content,
                                                'title': item.get('title', ''),
                                                'tags': item.get('tags', [])
                                            })
                            # Handle single object structure (fallback)
                            elif isinstance(data, dict) and 'content' in data:
                                content = data['content']
                                if content.strip():
                                    self.fragments.append({
                                        'source': filepath,
                                        'content': content
                                    })
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Error reading or parsing {filepath}: {e}")

        print(f"Loaded {len(self.fragments)} fragments.")

    def get_context(self, query, top_k=3):
        """
        Finds the most relevant context for a given query using keyword matching.
        """
        if not self.fragments:
            return ""

        # Simple keyword extraction: split query into words
        keywords = set(re.findall(r'\w+', query.lower()))
        if not keywords:
            return ""

        scored_fragments = []
        for fragment in self.fragments:
            fragment_words = set(re.findall(r'\w+', fragment['content'].lower()))
            score = len(keywords.intersection(fragment_words))
            
            if score > 0:
                scored_fragments.append({
                    'score': score,
                    'fragment': fragment
                })

        # Sort by score (descending)
        scored_fragments.sort(key=lambda x: x['score'], reverse=True)

        # Get top_k fragments
        top_fragments = [item['fragment']['content'] for item in scored_fragments[:top_k]]
        
        return "\n\n".join(top_fragments)

if __name__ == '__main__':
    # Example usage for testing
    # Adjust paths as per your project structure
    json_paths = [
        'resources/resurse_pbinfo/clasa_9_json',
        'resources/resurse_pbinfo/clasa_10_json_simple',
    ]
    optimizer = ContextOptimizer(json_paths)

    # Test query
    test_query = "ce este un vector?"
    context = optimizer.get_context(test_query)
    
    print(f"\n--- Context for query: '{test_query}' ---")
    print(context)
    
    test_query_2 = "sortare prin selectie"
    context_2 = optimizer.get_context(test_query_2)
    print(f"\n--- Context for query: '{test_query_2}' ---")
    print(context_2) 