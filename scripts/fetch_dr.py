import re
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import time

class RateLimitError(Exception):
    pass

def extract_domain(url):
    try:
        netloc = urllib.parse.urlparse(url).netloc
        if not netloc:
            if '/' in url:
                netloc = url.split('/')[0]
            else:
                netloc = url
        netloc = netloc.split(':')[0]
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc.lower().strip()
    except Exception:
        return ""

def is_excluded_directory(name, url):
    domain = extract_domain(url)
    if domain:
        excluded = {'reddit.com', 'github.com', 'facebook.com', 'fb.com', 'x.com', 'twitter.com'}
        for excl in excluded:
            if domain == excl or domain.endswith('.' + excl):
                return True
    name_lower = name.lower().strip()
    for prefix in ('r/', 'x/', 'fb/', 'gh/'):
        if name_lower.startswith(prefix):
            return True
    return False

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

def fetch_domain_rating(domain, api_key=None):
    if not api_key:
        api_key = os.getenv('AHREFS_API_KEY')

    url = f"https://api.ahrefs.com/v3/public/domain-rating-free?target={urllib.parse.quote(domain)}"
    headers = {
        'Accept': 'application/json',
    }

    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"
    else:
        # Fallback headers if calling without API key
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        headers['Referer'] = 'https://ahrefs.com/website-authority-checker'
        headers['Origin'] = 'https://ahrefs.com'

    req = urllib.request.Request(url, headers=headers)
    try:
        # Sleep for a bit to avoid hitting rate limits (polite delay)
        time.sleep(2.0)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            dr_obj = data.get('domain_rating', {})
            if 'domain_rating' in dr_obj:
                return int(dr_obj['domain_rating'])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"Rate limit hit (429) while fetching DR for {domain}.")
            raise RateLimitError("Rate limit hit")
        elif e.code in (401, 403):
            if not api_key:
                print(f"HTTP {e.code} for {domain}: Ahrefs APIv3 key missing. Add AHREFS_API_KEY to your environment (https://app.ahrefs.com/account/api-keys).")
            else:
                print(f"HTTP error {e.code} (Forbidden/Unauthorized) for {domain}. Check your AHREFS_API_KEY.")
        else:
            print(f"HTTP error {e.code} for {domain}")
    except Exception as e:
        print(f"Error fetching DR for {domain}: {e}")
    return None

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(current_dir, '..', 'README.md')
    json_path = os.path.join(current_dir, '..', 'launchdb.json')

    # Load current json entries
    if not os.path.exists(json_path):
        print(f"JSON database file not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        directories = json.load(f)

    # We need to map clean URLs to their DR to update README
    url_to_dr = {}
    updated_any = False
    rate_limited = False

    fetch_queue = []

    for entry in directories:
        name = entry.get('name', '')
        url = entry.get('submission_link', '')
        
        # Strip UTM/via parameters for matching
        try:
            parsed = urllib.parse.urlparse(url)
            qsl = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k not in ('utm_source', 'via')]
            new_query = urllib.parse.urlencode(qsl)
            parsed = parsed._replace(query=new_query)
            clean_url = urllib.parse.urlunparse(parsed)
        except Exception:
            clean_url = url

        if is_excluded_directory(name, url):
            entry['domain_rating'] = None
            url_to_dr[clean_url] = None
            continue

        dr_val = entry.get('domain_rating')
        last_updated_str = entry.get('dr_last_updated')
        url_to_dr[clean_url] = dr_val

        # Check if we need to fetch and set priority (1: missing/null DR, 2: outdated DR >= 30 days)
        needs_fetch = False
        priority = 0
        if dr_val is None:
            needs_fetch = True
            priority = 1
        elif not last_updated_str:
            needs_fetch = True
            priority = 1
        else:
            try:
                last_updated = datetime.datetime.strptime(last_updated_str, '%Y-%m-%d').date()
                if (datetime.date.today() - last_updated).days >= 30:
                    needs_fetch = True
                    priority = 2
            except ValueError:
                needs_fetch = True
                priority = 1

        if needs_fetch:
            fetch_queue.append((priority, entry, clean_url))

    # Sort queue: entries with missing DR (priority 1) are processed FIRST
    fetch_queue.sort(key=lambda x: x[0])

    print(f"Total entries queued for DR check: {len(fetch_queue)} (Missing DR: {sum(1 for p, _, _ in fetch_queue if p == 1)}, Outdated DR: {sum(1 for p, _, _ in fetch_queue if p == 2)})")

    for priority, entry, clean_url in fetch_queue:
        if rate_limited:
            break

        name = entry.get('name', '')
        url = entry.get('submission_link', '')
        domain = extract_domain(url)
        if not domain:
            continue

        print(f"Fetching DR for {domain} ({name})...")
        try:
            new_dr = fetch_domain_rating(domain)
            if new_dr is not None:
                entry['domain_rating'] = new_dr
                entry['dr_last_updated'] = datetime.date.today().strftime('%Y-%m-%d')
                url_to_dr[clean_url] = new_dr
                updated_any = True
                print(f"-> Success: DR = {new_dr}")
            else:
                print(f"-> Could not retrieve DR for {domain}")
        except RateLimitError:
            rate_limited = True
            print("Rate limit reached. Halting further DR requests for this run.")
            break

    # Save updated json database
    if updated_any:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(directories, f, indent=2, ensure_ascii=False)
        print("Updated launchdb.json.")

    # Re-read README and update rows with new DR values
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        table_pattern = re.compile(r'(\|.*?\|\n\|.*?\|\n(?:\|.*?\|\n)*)')
        match = table_pattern.search(content)
        if match:
            table_text = match.group(1)
            lines = table_text.strip().split('\n')
            
            new_lines = []
            readme_updated = False
            
            for i, line in enumerate(lines):
                if i < 2:
                    new_lines.append(line)
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 6:
                    link_col = parts[5].strip()
                    url_match = re.search(r'\]\((.*?)\)', link_col)
                    link_url = url_match.group(1).strip() if url_match else link_col
                    
                    try:
                        parsed = urllib.parse.urlparse(link_url)
                        qsl = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k not in ('utm_source', 'via')]
                        new_query = urllib.parse.urlencode(qsl)
                        parsed = parsed._replace(query=new_query)
                        clean_link_url = urllib.parse.urlunparse(parsed)
                    except Exception:
                        clean_link_url = link_url
                        
                    if clean_link_url in url_to_dr:
                        dr_val = url_to_dr[clean_link_url]
                        dr_str = str(dr_val) if dr_val is not None else '-'
                        if parts[4].strip() != dr_str:
                            parts[4] = f' {dr_str} '
                            readme_updated = True
                    new_lines.append('|'.join(parts))
                else:
                    new_lines.append(line)
                    
            if readme_updated:
                new_table_text = '\n'.join(new_lines) + '\n'
                new_content = content.replace(table_text, new_table_text)
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("Updated README.md table with Domain Ratings.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error executing fetch_dr script: {e}")
