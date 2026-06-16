import re
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from generate_json import generate_json

def add_utm_to_url(url, utm_source="launchdb.vercel.app", via="launchdb"):
    if not url or not url.startswith('http'):
        return url
        
    try:
        parsed = urlparse(url)
        qsl = parse_qsl(parsed.query)
        
        utm_found = False
        via_found = False
        new_qsl = []
        for k, v in qsl:
            if k == 'utm_source':
                utm_found = True
                if v != utm_source:
                    new_qsl.append((k, utm_source))
                else:
                    new_qsl.append((k, v))
            elif k == 'via':
                via_found = True
                if v != via:
                    new_qsl.append((k, via))
                else:
                    new_qsl.append((k, v))
            else:
                new_qsl.append((k, v))
                
        if not utm_found:
            new_qsl.append(('utm_source', utm_source))
        if not via_found:
            new_qsl.append(('via', via))
            
        new_query = urlencode(new_qsl)
        if new_query != parsed.query:
            parsed = parsed._replace(query=new_query)
            return urlunparse(parsed)
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        
    return url


def process_readme(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the table block
    table_pattern = re.compile(r'(\|.*?\|\n\|.*?\|\n(?:\|.*?\|\n)*)')
    match = table_pattern.search(content)
    if not match:
        print("Could not find table in README.md")
        return False

    table_text = match.group(1)
    lines = table_text.strip().split('\n')
    
    new_lines = []
    changes_made = False
    
    for i, line in enumerate(lines):
        if i < 2:
            new_lines.append(line)
            continue # skip header and separator
            
        parts = line.split('|')
        if len(parts) >= 5:
            link_col = parts[4].strip()
            # Extract URL from markdown link format [text](url)
            url_match = re.search(r'\[(.*?)\]\((.*?)\)', link_col)
            
            if url_match:
                link_text = url_match.group(1)
                url = url_match.group(2).strip()
                
                new_url = add_utm_to_url(url)
                if new_url != url:
                    parts[4] = f' [{link_text}]({new_url}) '
                    changes_made = True
            else:
                # Raw URL
                new_url = add_utm_to_url(link_col)
                if new_url != link_col:
                    parts[4] = f' {new_url} '
                    changes_made = True
            
            new_lines.append('|'.join(parts))
        else:
            new_lines.append(line)
            
    new_table_text = '\n'.join(new_lines) + '\n'
    
    if changes_made:
        new_content = content.replace(table_text, new_table_text)
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated README.md links with UTM parameters.")
        return True
    else:
        print("All README.md links already have UTM parameters.")
        return False

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(current_dir, '..', 'README.md')
    json_path = os.path.join(current_dir, '..', 'launchdb.json')
    
    # Process README
    readme_updated = process_readme(readme_path)
    
    # Regenerate launchdb.json
    generate_json(readme_path, json_path)
