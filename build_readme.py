import argparse
import httpx
import json
import pathlib
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

root = pathlib.Path(__file__).parent.resolve()

def replace_chunk(content, marker, chunk):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    chunk = "<!-- {} starts -->\n{}\n<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def fetch_thesis_updates(url):
    print(url)
    response = httpx.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    updates = []
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = heading.text.strip()
        anchor = "#" + text.lower().replace(' ', '-')
        updates.append((text, f"{url}{anchor}"))
        
    if updates:
        return updates

def load_data(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def update_helper_file(filepath, all_updates):
    data = load_data(filepath)
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    updated = False

    for updates in all_updates:
        for text, link in updates:
            if not any(d['link'] == link for d in data):
                data.append({'text': text, 'link': link, 'date': current_date})
                updated = True

    if updated:
        save_data(filepath, data)

def get_recent_updates(filepath, count=5):
    data = load_data(filepath)
    sorted_data = sorted(data, key=lambda x: x['date'], reverse=True)
    return sorted_data[:count]

def fetch_github_files(owner, repo, path, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {'Authorization': f'token {token}'}
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        files = [item['name'] for item in response.json() if item['type'] == 'file' and item['name'].endswith('.md')]
        files = [file.replace('.md', '') for file in files]
        return files
    else:
        print(f"Failed to fetch files: {response.status_code}")
        print(f"Response: {response.text}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update README with the latest thesis updates.")
    parser.add_argument('--api_key', required=True, help='GitHub API key for accessing repository data')
    args = parser.parse_args()

    readme = root / "README.md"
    with readme.open("r", encoding='utf-8') as file:
        readme_contents = file.read()

    files = fetch_github_files('hslima00', 'Tese_md', 'Tese_md/Markdown', args.api_key)
    print(f"Files: {files}")
    base_url = "https://hslima00.github.io/Tese_md/"

    urls = [base_url + file + ('/' if file != 'index' else '') for file in files]

    all_updates = []
    for url in urls:
        updates = fetch_thesis_updates(url)
        all_updates.append(updates)

    update_helper_file('updates.json', all_updates)

    recent_updates = get_recent_updates('updates.json', count=5)
    recent_updates_md = "### Recent Updates\n\n| Update | Link | Date |\n| ------ | ---- | ---- |\n"
    for update in recent_updates:
        recent_updates_md += f"| {update['text']} | [Link]({update['link']}) | {update['date']} |\n"

    # Update README.md
    readme_contents = replace_chunk(readme_contents, "recent_updates", recent_updates_md)
    with readme.open("w", encoding='utf-8') as file:
        file.write(readme_contents)