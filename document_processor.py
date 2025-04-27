from docx import Document
from docx.shared import Pt
import os
from slugify import slugify
from urllib.parse import urlparse

def create_document(content, save_dir, url, index):
    if not os.path.exists(save_dir): 
        os.makedirs(save_dir)
    
    parsed = urlparse(url)
    base_name = slugify(parsed.path, separator="_") or "anasayfa"
    filename = f"{base_name}_{index}.docx"
    
    doc = Document()
    title = content[0]['text']
    h0 = doc.add_heading(title, level=0)
    h0.runs[0].font.size = Pt(14)
    
    for item in content[1:]:
        if item['type'] == 'header':
            h = doc.add_heading(level=item['level'])
            run = h.add_run(item['text'])
            run.bold = True
            run.font.size = Pt(14)
        elif item['type'] == 'paragraph':
            p = doc.add_paragraph()
            if 'parts' in item:
                for part in item['parts']:
                    run = p.add_run(part['text'])
                    if part['bold']:
                        run.bold = True
                    run.font.size = Pt(12)
            else:
                run = p.add_run(item['text'])
                run.font.size = Pt(12)
        elif item['type'] == 'list':
            for li in item['items']:
                p = doc.add_paragraph(style='List Bullet')
                if 'parts' in li:
                    for part in li['parts']:
                        run = p.add_run(part['text'])
                        if part['bold']:
                            run.bold = True
                        run.font.size = Pt(12)
                else:
                    run = p.add_run(li)
                    run.font.size = Pt(12)
    
    path = os.path.join(save_dir, filename)
    doc.save(path)
    return filename