import re
from bs4 import BeautifulSoup
import logging
from src.utils.common import normalize_company_name, normalize_transaction_value, parse_date, extract_company_names

logger = logging.getLogger(__name__)

class FormS4Parser:
    def __init__(self):
        self.sections = {
            "SUMMARY": [
                "The Merger",
                "The Companies",
                "The Business Combination",
                "Merger Consideration",
                "Exchange Ratio",
                "Summary of the Transaction",
                "Overview of the Transaction",
            ],
            "TERMS": [
                "Terms of the Merger",
                "Terms of the Transaction",
                "Merger Agreement",
                "Transaction Structure",
                "The Agreement and Plan of Merger",
            ],
            "RISK_FACTORS": [
                "Risk Factors",
                "Risks Related to the Merger",
                "Risks Related to the Business Combination",
                "Transaction Risks",
            ]
        }
        
        self.detail_patterns = {
            'exchange_ratio': [
                r'exchange ratio of\s+(\d+(?:\.\d+)?)',
                r'exchange ratio\s+(?:will be|is|of)\s+(\d+(?:\.\d+)?)\s+shares?',
                r'(?:will receive|to receive)\s+(\d+(?:\.\d+)?)\s+shares?.*?for each share',
            ],
            'shares_outstanding': [
                r'approximately\s+(\d+(?:,\d+)*)\s+shares?\s+(?:outstanding|issued)',
                r'(\d+(?:,\d+)*)\s+shares?\s+(?:will be|are)\s+(?:outstanding|issued)',
                r'total\s+(?:of\s+)?(\d+(?:,\d+)*)\s+shares?\s+(?:outstanding|issued)',
            ],
            'voting_threshold': [
                r'(\d+(?:\.\d+)?%)\s+of the outstanding',
                r'requires?\s+(?:the\s+)?approval\s+of\s+(\d+(?:\.\d+)?%)',
                r'majority\s+\((\d+(?:\.\d+)?%)\)',
            ],
        }

    def extract_section_content(self, soup, section_titles):
        for title in section_titles:
            patterns = [
                title,
                title.upper(),
                title.title(),
            ]
            
            for pattern in patterns:
                section = soup.find(text=re.compile(pattern))
                if section:
                    parent = section.find_parent()
                    if parent:
                        content = []
                        current = parent.next_sibling
                        while current:
                            if isinstance(current, str):
                                if any(re.search(p, str(current)) for p in patterns):
                                    break
                                content.append(current.strip())
                            elif current.name:
                                if any(re.search(p, str(current.text)) for p in patterns):
                                    break
                                content.append(current.get_text().strip())
                            current = current.next_sibling
                        return " ".join(filter(None, content))
        return None

    def extract_transaction_details(self, text):
        if not text:
            return {}
        
        details = {}
        
        value_patterns = [
            r"transaction value of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"total consideration of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"merger consideration of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"aggregate value of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"total transaction value of\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
            r"valued at\s+\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|m|b)?",
        ]
        
        for pattern in value_patterns:
            value_match = re.search(pattern, text, re.IGNORECASE)
            if value_match:
                value_str = value_match.group(0)
                details['transaction_value'] = normalize_transaction_value(value_str)
                break
        
        acquirer, target = extract_company_names(text)
        if acquirer:
            details['acquirer'] = acquirer
        if target:
            details['target'] = target
        
        date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        date_matches = re.finditer(date_pattern, text)
        for match in date_matches:
            date_str = match.group()
            context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            if re.search(r'announce|sign|enter|agree|date of', context, re.IGNORECASE):
                details['transaction_date'] = date_str
                break
        
        for key, patterns in self.detail_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    details[key] = match.group(1)
                    break
        
        return details

    def parse_filing(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'lxml')
            
            all_text = []
            for section_type, section_titles in self.sections.items():
                section_content = self.extract_section_content(soup, section_titles)
                if section_content:
                    all_text.append(section_content)
            
            if not all_text:
                all_text = [soup.get_text()]

            combined_text = " ".join(all_text)
            details = self.extract_transaction_details(combined_text)
            
            if details:
                return details
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing filing {file_path}: {e}")
            return None 