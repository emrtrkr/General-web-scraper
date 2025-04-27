import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import hashlib

def fetch_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        return None

def is_valid_url(u):
    parsed = urlparse(u)
    return bool(parsed.scheme and parsed.netloc)

def get_all_website_links(url, base_domain):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        urls = set()
        for a in soup.find_all('a', href=True):
            href = urljoin(url, a['href'])
            p = urlparse(href)
            clean = f"{p.scheme}://{p.netloc}{p.path}"
            if p.netloc == base_domain and clean not in urls and is_valid_url(clean):
                if not any(clean.endswith(ext) for ext in ['.pdf','.jpg','.png','.zip']):
                    urls.add(clean)
        return urls
    except Exception as e:
        return []

def is_main_content(el):
    return el.find_parent(['header','footer','nav','aside']) is None

def process_content(soup, opts):
    content = []
    title = soup.title.string.strip() if soup.title and soup.title.string else 'Başlıksız'
    content.append({'type':'title','text':title})
    
    tags = []
    header_tags = []
    for lvl in range(1,7):
        if opts.get(f'h{lvl}'):
            header_tags.append(f'h{lvl}')
            tags.append(f'h{lvl}')
    if opts['p']: tags.append('p')
    if opts['lists']: tags.extend(['ul','ol'])
    if opts['headers']: tags.append('header')
    if opts['footers']: tags.append('footer')
    if opts['span']: tags.append('span')
    
    unwanted_classes = [
        'dropdown', 'menu', 'navigation', 'nav', 'sidebar', 'footer', 'header',
        'popup', 'modal', 'cookie', 'banner', 'alert', 'notification',
        'advertisement', 'ad', 'widget', 'social', 'share', 'search',
        'login', 'cart', 'newsletter', 'subscribe'
    ]
    
    wanted_special_classes = [
        'accordion', 'faq', 'soru', 'cevap', 'question', 'answer', 
        'sss', 'sıkça-sorulan', 'sikca-sorulan', 'collapsible',
        'toggle', 'expand', 'vss', 'vs-soru', 'faq-item'
    ]

    def should_process_element(elem):
        if not is_main_content(elem):
            return False
            
        if elem.name == 'span' and opts['span']:
            current = elem
            while current and current.name != 'body':
                if current.get('class'):
                    class_names = ' '.join(current.get('class')).lower()
                    if any(wanted in class_names for wanted in wanted_special_classes):
                        return True
                if current.get('id'):
                    id_name = current.get('id').lower()
                    if any(wanted in id_name for wanted in wanted_special_classes):
                        return True
                current = current.parent
            return False
            
        if not opts['div']:
            if elem.name == 'div' or elem.find_parents('div'):
                if opts.get('filter_divs', True):
                    current = elem
                    while current and current.name != 'body':
                        if current.get('class'):
                            class_names = ' '.join(current.get('class')).lower()
                            if any(wanted in class_names for wanted in wanted_special_classes):
                                return True
                            if any(unwanted in class_names for unwanted in unwanted_classes):
                                return False
                        if current.get('id'):
                            id_name = current.get('id').lower()
                            if any(wanted in id_name for wanted in wanted_special_classes):
                                return True
                            if any(unwanted in id_name for unwanted in unwanted_classes):
                                return False
                        current = current.parent
                    return True
                else:
                    return False
                    
        return True
    
    for elem in soup.body.find_all(tags, recursive=True):
        if not should_process_element(elem):
            continue
            
        name = elem.name
        if name in header_tags:
            text = elem.get_text(strip=True)
            if text:
                content.append({'type':'header','level':int(name[1]),'text':text})
        elif name == 'p':
            bold_parts = []
            for content_part in elem.contents:
                if content_part.name in ['b', 'strong']:
                    bold_parts.append({'text': content_part.get_text(strip=True), 'bold': True})
                elif content_part.string and content_part.string.strip():
                    bold_parts.append({'text': content_part.string.strip(), 'bold': False})
            
            if bold_parts:
                content.append({'type':'paragraph','parts':bold_parts})
        elif name in ('ul','ol'):
            items = []
            for li in elem.find_all('li', recursive=False):
                if li.find('a'): continue
                bold_parts = []
                for content_part in li.contents:
                    if content_part.name in ['b', 'strong']:
                        bold_parts.append({'text': content_part.get_text(strip=True), 'bold': True})
                    elif content_part.string and content_part.string.strip():
                        bold_parts.append({'text': content_part.string.strip(), 'bold': False})
                
                if bold_parts:
                    items.append({'parts': bold_parts})
            if items:
                content.append({'type':'list','items':items})
        elif name == 'div':
            direct = ' '.join(t.strip() for t in elem.find_all(text=True, recursive=False) if t.strip())
            if direct:
                content.append({'type':'paragraph','text':direct})
        elif name == 'span' and opts['span']:
            text = elem.get_text(strip=True, separator=' ')
            if text:
                content.append({'type':'paragraph','text':text})
        elif name == 'header' and opts['headers']:
            txt = elem.get_text(strip=True)
            if txt:
                content.append({'type':'paragraph','text':txt})
        elif name == 'footer' and opts['footers']:
            txt = elem.get_text(strip=True)
            if txt:
                content.append({'type':'paragraph','text':txt})
    
    return content

def hash_content(content):
    hash_str = ""
    for item in content:
        hash_str += f"{item['type']}_{item.get('level','')}_{item.get('text','')}".lower()
    return hashlib.md5(hash_str.encode()).hexdigest()