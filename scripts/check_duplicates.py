import re
import os

def check_duplicates(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the table block
    table_pattern = re.compile(r'(\|.*?\|\n\|.*?\|\n(?:\|.*?\|\n)*)')
    match = table_pattern.search(content)
    if not match:
        print("Could not find table in README.md")
        return

    table_text = match.group(1)
    lines = table_text.strip().split('\n')
    
    names = {}
    urls = {}
    
    duplicates = []
    
    for i, line in enumerate(lines):
        if i < 2:
            continue # skip header and separator
            
        parts = line.split('|')
        if len(parts) >= 6:
            # Format is usually: | # | Name | Description | Domain Rating | Link |
            name = parts[2].strip()
            # Clean up the name from markdown bolding
            name = name.replace('**', '')
            
            link_col = parts[5].strip()
            # Extract URL from markdown link format [text](url)
            url_match = re.search(r'\]\((.*?)\)', link_col)
            url = url_match.group(1).strip() if url_match else link_col
            
            if name.lower() in names:
                duplicates.append(f"Duplicate Name: '{name}' at line {i+1} and {names[name.lower()]}")
            else:
                names[name.lower()] = i+1
                
            if url.lower() in urls:
                duplicates.append(f"Duplicate URL: '{url}' at line {i+1} and {urls[url.lower()]}")
            else:
                urls[url.lower()] = i+1
                
    if duplicates:
        print("Found the following duplicates:")
        for dup in duplicates:
            print("- " + dup)
    else:
        print("No duplicates found!")

if __name__ == "__main__":
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    check_duplicates(readme_path)
