import re
import os
import json
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def generate_json(readme_path, json_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the table block
    table_pattern = re.compile(r'(\|.*?\|\n\|.*?\|\n(?:\|.*?\|\n)*)')
    match = table_pattern.search(content)
    if not match:
        print("Could not find table in README.md")
        return

    table_text = match.group(1)
    lines = table_text.strip().split('\n')
    
    directories = []
    
    for i, line in enumerate(lines):
        if i < 2:
            continue # skip header and separator
            
        parts = [p.strip() for p in line.split('|')]
        # Parts will be: ['', '#', 'Name', 'Description', 'Link', '']
        if len(parts) >= 5:
            name = parts[2]
            # Clean up the name from markdown bolding
            name = name.replace('**', '')
            
            description = parts[3]
            
            link_col = parts[4]
            # Extract URL from markdown link format [text](url)
            url_match = re.search(r'\]\((.*?)\)', link_col)
            url = url_match.group(1).strip() if url_match else link_col
            
            # Remove utm_source and via query parameters if present (only keep them in README.md)
            try:
                parsed = urlparse(url)
                qsl = [(k, v) for k, v in parse_qsl(parsed.query) if k not in ('utm_source', 'via')]
                new_query = urlencode(qsl)
                parsed = parsed._replace(query=new_query)
                url = urlunparse(parsed)
            except Exception as e:
                print(f"Error removing UTM/via from URL {url}: {e}")
            
            # Extract serial number/id
            try:
                entry_id = int(parts[1])
            except ValueError:
                entry_id = i - 1
            
            # Check if name is not empty
            if name:
                directories.append({
                    "id": entry_id,
                    "name": name,
                    "description": description,
                    "submission_link": url
                })
                
    # Write to directories.json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(directories, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated {json_path} with {len(directories)} entries.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(current_dir, '..', 'README.md')
    json_path = os.path.join(current_dir, '..', 'launchdb.json')
    generate_json(readme_path, json_path)
