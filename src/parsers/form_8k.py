import re
from bs4 import BeautifulSoup
import logging
from src.utils.common import (
    normalize_company_name,
    normalize_transaction_value,
    parse_date,
    clean_html_text,
    extract_filing_header,
    extract_company_names
)

class Form8KParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ma_patterns = [
            r"merger",
            r"acquisition",
            r"business combination",
            r"purchase agreement",
            r"definitive agreement",
            r"asset purchase",
            r"stock purchase",
        ]
        
        self.ma_items = {
            "1.01": "Entry into a Material Definitive Agreement",
            "2.01": "Completion of Acquisition or Disposition of Assets",
            "9.01": "Financial Statements and Exhibits"
        }

    def extract_item_content(self, text, item_number):
        patterns = [
            f"Item {item_number}",
            f"ITEM {item_number}",
            f"Item{item_number}",
            f"ITEM{item_number}"
        ]
        
        for pattern in patterns:
            item_match = re.search(f"{pattern}[^a-zA-Z0-9]+(.*?)(?=Item \d|\Z)", text, re.DOTALL | re.IGNORECASE)
            if item_match:
                return item_match.group(1).strip()
        return None

    def contains_ma_content(self, text):
        if not text:
            return False
        
        text = text.lower()
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.ma_patterns)

    def extract_transaction_details(self, text, header_info):
        if not text:
            return {}
        
        details = {
            'acquirer': None,
            'target': None,
            'transaction_date': None,
            'transaction_value': None
        }
        
        acquirer, target = extract_company_names(text)
        if acquirer:
            details['acquirer'] = acquirer
        if target:
            details['target'] = target
                    
        if not details['acquirer'] and not details['target'] and header_info.get('company_name'):
            details['acquirer'] = normalize_company_name(header_info['company_name'])
        
        value_patterns = [
            r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?\s+(?:transaction|deal|consideration|purchase price|offer)",
            r"(?:transaction|deal|consideration|purchase|offer)\s+(?:price|value|amount)\s+of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"total\s+(?:value|consideration|amount)\s+of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
        ]
        
        for pattern in value_patterns:
            value_match = re.search(pattern, text, re.IGNORECASE)
            if value_match:
                value_str = value_match.group(0)
                details['transaction_value'] = normalize_transaction_value(value_str)
                break
        
        date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        date_matches = re.finditer(date_pattern, text)
        for match in date_matches:
            date_str = match.group()
            context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            if re.search(r'announce|sign|enter|agree', context, re.IGNORECASE):
                details['transaction_date'] = parse_date(date_str)
                break
        
        return details

    def parse_filing(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            header_info = extract_filing_header(content)
            text = clean_html_text(content)
            
            ma_content = []
            for item_number, item_desc in self.ma_items.items():
                item_content = self.extract_item_content(text, item_number)
                if item_content and self.contains_ma_content(item_content):
                    ma_content.append(item_content)
            
            if ma_content:
                combined_content = ' '.join(ma_content)
                details = self.extract_transaction_details(combined_content, header_info)
                
                if any(details.values()):
                    return {
                        'form_type': '8-K',
                        'file_path': file_path,
                        **details
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing filing {file_path}: {e}")
            return None 