import re
import logging
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def clean_html_text(html_content):
    try:
        text_match = re.search(r'<TEXT>(.*?)</TEXT>', html_content, re.DOTALL)
        if text_match:
            html_content = text_match.group(1)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
            
        lines = []
        for element in soup.stripped_strings:
            line = element.strip()
            if line:
                lines.append(line)
                
        text = ' '.join(lines)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {str(e)}")
        return html_content

def extract_filing_header(text):
    header_info = {
        'company_name': None,
        'cik': None,
        'form_type': None,
        'filing_date': None,
        'business_address': None
    }
    
    try:
        company_match = re.search(r'COMPANY CONFORMED NAME:\s*(.+?)(?:\n|$)', text)
        if company_match:
            header_info['company_name'] = company_match.group(1).strip()
            
        cik_match = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', text)
        if cik_match:
            header_info['cik'] = cik_match.group(1).strip()
            
        form_match = re.search(r'CONFORMED SUBMISSION TYPE:\s*(.+?)(?:\n|$)', text)
        if form_match:
            header_info['form_type'] = form_match.group(1).strip()
            
        date_match = re.search(r'FILED AS OF DATE:\s*(\d{8})', text)
        if date_match:
            date_str = date_match.group(1)
            header_info['filing_date'] = datetime.strptime(date_str, '%Y%m%d').date()
            
        address_pattern = r'BUSINESS ADDRESS:.*?STREET 1:\s*(.+?)(?:\n|$).*?CITY:\s*(.+?)(?:\n|$).*?STATE:\s*(.+?)(?:\n|$).*?ZIP:\s*(.+?)(?:\n|$)'
        address_match = re.search(address_pattern, text, re.DOTALL)
        if address_match:
            street = address_match.group(1).strip()
            city = address_match.group(2).strip()
            state = address_match.group(3).strip()
            zip_code = address_match.group(4).strip()
            header_info['business_address'] = f"{street}, {city}, {state} {zip_code}"
            
    except Exception as e:
        logger.error(f"Error extracting filing header information: {str(e)}")
        
    return header_info

def normalize_company_name(name):
    if not name:
        return None
        
    suffixes = [
        r'\s*,?\s*Inc\.?',
        r'\s*,?\s*Corp\.?',
        r'\s*,?\s*Corporation',
        r'\s*,?\s*Company',
        r'\s*,?\s*Co\.?',
        r'\s*,?\s*Ltd\.?',
        r'\s*,?\s*LLC',
        r'\s*,?\s*L\.?L\.?C\.?',
        r'\s*,?\s*Limited',
        r'\s*,?\s*Holdings?',
        r'\s*,?\s*Group',
        r'\s*,?\s*International',
        r'\s*,?\s*Incorporated',
        r'\s*,?\s*PLC',
        r'\s*,?\s*AG',
        r'\s*,?\s*SE',
        r'\s*,?\s*SA',
        r'\s*,?\s*NV',
        r'\s*,?\s*BV',
    ]
    
    name = name.strip()
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[,.]$', '', name)
    name = name.strip()
    
    return name

def normalize_transaction_value(value_str):
    if not value_str:
        return None
        
    try:
        match = re.search(r'\$([\d,.]+)\s*(million|billion|m|b|M|B)?', value_str)
        if not match:
            return None
            
        value = float(match.group(1).replace(',', ''))
        multiplier = match.group(2).lower() if match.group(2) else ''
        
        if multiplier in ['billion', 'b']:
            value *= 1_000_000_000
        elif multiplier in ['million', 'm']:
            value *= 1_000_000
            
        return value
    except Exception as e:
        logger.error(f"Error normalizing transaction value '{value_str}': {str(e)}")
        return None

def parse_date(date_str):
    if not date_str:
        return None
        
    try:
        date_str = re.sub(r'^(?:dated|as of|entered into on|executed on|signed on)\s*', '', date_str, flags=re.IGNORECASE) 
        formats = [
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d-%b-%Y',
            '%d %B %Y',
            '%Y%m%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
                
        return None
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {str(e)}")
        return None

def extract_company_names(text, context_size=200):
    try:
        patterns = [
            r'(?P<acquirer>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))(?:\s*\([^)]+\))?\s*(?:will acquire|to acquire|has agreed to acquire|is acquiring)\s*(?P<target>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))',
            r'(?P<acquirer>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))(?:\s*\([^)]+\))?\s*(?:will merge with|to merge with|has agreed to merge with)\s*(?P<target>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))',
            r'(?P<target>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))(?:\s*\([^)]+\))?\s*(?:will be acquired by|to be acquired by|has agreed to be acquired by)\s*(?P<acquirer>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))',
            r'(?P<acquirer>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))(?:\s*\([^)]+\))?\s*(?:entered into|has entered into|executed|signed)\s*(?:a|an)\s*(?:merger agreement|agreement and plan of merger)\s*with\s*(?P<target>[A-Z][A-Za-z\s,\.&]+?(?:Corporation|Corp|Inc|Bancorp|Company|Co|Ltd|LLC|Bank(?:\s*&\s*Trust)?))'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                acquirer = match.group('acquirer').strip()
                target = match.group('target').strip()
                start = max(0, match.start() - context_size)
                end = min(len(text), match.end() + context_size)
                context = text[start:end]
                
                if re.search(r'merger|acquisition|combine|transaction|deal', context, re.IGNORECASE):
                    return normalize_company_name(acquirer), normalize_company_name(target)
        
        header_info = extract_filing_header(text)
        if header_info and header_info['company_name']:
            return normalize_company_name(header_info['company_name']), None
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error extracting company names: {str(e)}")
        return None, None

def combine_daily_data(processed_dir, start_date=None, end_date=None):
    all_data = []
    
    for parquet_file in processed_dir.glob('ma_data_*.parquet'):
        try:
            date_str = re.search(r'ma_data_(\d{8})\.parquet', parquet_file.name).group(1)
            date = datetime.strptime(date_str, '%Y%m%d')
            
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
                
            df = pd.read_parquet(parquet_file)
            all_data.append(df)
            
        except Exception as e:
            print(f"Error reading {parquet_file}: {e}")
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame() 