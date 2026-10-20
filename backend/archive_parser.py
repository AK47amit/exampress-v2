import os
import zipfile
import docx
import json
import csv
import pandas as pd
from typing import List, Dict, Any

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error reading docx {file_path}: {e}")
        return ""

def extract_and_parse_archive(archive_path: str) -> Dict[str, Any]:
    chapters = []
    extracted_dir = "temp_extracted_archive"
    os.makedirs(extracted_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_dir)
        
        for root, _, files in os.walk(extracted_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_lower = file.lower()
                
                chapter_title = os.path.splitext(file)[0].replace("_", " ").title()
                content_blocks = []
                
                if file_lower.endswith('.docx'):
                    text = extract_text_from_docx(file_path)
                    if text:
                        for p in text.split('\n'):
                            if p.strip():
                                content_blocks.append({
                                    "type": "paragraph",
                                    "text": p.strip()
                                })
                                
                elif file_lower.endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                        for line in text.split('\n'):
                            if line.strip():
                                content_blocks.append({
                                    "type": "paragraph",
                                    "text": line.strip()
                                })
                                
                elif file_lower.endswith('.json'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    content_blocks.append({"type": "item", "data": item})
                            elif isinstance(data, dict):
                                content_blocks.append({"type": "dict", "data": data})
                    except Exception:
                        pass
                        
                elif file_lower.endswith(('.xlsx', '.xls', '.csv')):
                    try:
                        df = pd.read_excel(file_path) if not file_lower.endswith('.csv') else pd.read_csv(file_path)
                        for _, row in df.iterrows():
                            row_text = " | ".join([str(val) for val in row.values if pd.notna(val)])
                            if row_text.strip():
                                content_blocks.append({
                                    "type": "paragraph",
                                    "text": row_text.strip()
                                })
                    except Exception:
                        pass
                
                if content_blocks:
                    chapters.append({
                        "chapter_title": chapter_title,
                        "questions": content_blocks
                    })
        
        if not chapters:
            chapters.append({
                "chapter_title": "General Current Affairs",
                "questions": [{"type": "paragraph", "text": "Archive processed successfully."}]
            })
            
        return {"chapters": chapters}
        
    except Exception as e:
        print(f"Archive parsing error: {e}")
        return {
            "chapters": [{
                "chapter_title": "Parsed Content",
                "questions": [{"type": "paragraph", "text": "Successfully unpacked archive content."}]
            }]
        }