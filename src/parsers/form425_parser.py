import re
import logging
from bs4 import BeautifulSoup
from src.utils.common import (
    normalize_company_name,
    normalize_transaction_value,
    parse_date,
    clean_html_text,
    extract_filing_header,
    extract_company_names
)

class Form425Parser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ma_patterns = {
            'merger_agreement': r'(?i)(entered into|executed|signed).*?(merger agreement|agreement and plan of merger)',
            'consideration': r'(?i)(exchange ratio|merger consideration|conversion ratio|receive).{0,50}(\$[\d,.]+|[\d.]+\s*shares?)',
            'closing_date': r'(?i)(expected to close|anticipated closing|completion).{0,50}(in|by|during).{0,50}([QQ][1-4]|first|second|third|fourth).{0,20}(quarter|qtr).{0,20}(202[4-9])',
            'termination_fee': r'(?i)(termination fee|break.?up fee).{0,50}\$[\d,.]+\s*(million|billion)?',
        }
        
    def extract_transaction_details(self, text, header_info):
        details = {
            'acquirer': None,
            'target': None,
            'transaction_date': None,
            'transaction_value': None,
            'exchange_ratio': None,
            'termination_fee': None,
            'expected_closing': None
        }
        
        companies = extract_company_names(text)
        if companies:
            for company in companies:
                if company['acquirer'] and company['target']:
                    details['acquirer'] = company['acquirer']
                    details['target'] = company['target']
                    break
                    
        if not details['acquirer'] and not details['target'] and header_info.get('company_name'):
            details['acquirer'] = normalize_company_name(header_info['company_name'])
            
        consideration_match = re.search(self.ma_patterns['consideration'], text, re.IGNORECASE)
        if consideration_match:
            consideration_text = consideration_match.group(0)
            ratio_match = re.search(r'([\d.]+)\s*shares?', consideration_text)
            if ratio_match:
                details['exchange_ratio'] = float(ratio_match.group(1))
            cash_match = re.search(r'\$([\d,.]+)\s*(million|billion)?', consideration_text)
            if cash_match:
                details['transaction_value'] = normalize_transaction_value(cash_match.group(0))
                
        fee_match = re.search(self.ma_patterns['termination_fee'], text, re.IGNORECASE)
        if fee_match:
            fee_text = fee_match.group(0)
            fee_value_match = re.search(r'\$([\d,.]+)\s*(million|billion)?', fee_text)
            if fee_value_match:
                details['termination_fee'] = normalize_transaction_value(fee_value_match.group(0))
                
        closing_match = re.search(self.ma_patterns['closing_date'], text, re.IGNORECASE)
        if closing_match:
            details['expected_closing'] = closing_match.group(0)
            
        date_pattern = r'(?:dated|as of|entered into on|executed on|signed on)\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*\d{1,2},\s*202[4-9]'
        date_match = re.search(date_pattern, text, re.IGNORECASE)
        if date_match:
            details['transaction_date'] = parse_date(date_match.group(0))
            
        return details
        
    def parse_filing(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            header_info = extract_filing_header(content)
            text = clean_html_text(content)
            details = self.extract_transaction_details(text, header_info)
            
            if any(v for k, v in details.items() if k not in ['form_type', 'file_path']):
                return {
                    'form_type': '425',
                    'file_path': file_path,
                    **details
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing Form 425 filing {file_path}: {str(e)}")
            
        return None 