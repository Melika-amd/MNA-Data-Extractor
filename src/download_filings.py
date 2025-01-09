import os
import re
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

class SECDownloader:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.sec.gov/Archives"
        self.headers = {
            'User-Agent': 'Mel Project (mel@example.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        
    def download_daily_index(self, date):
        try:
            year = date.strftime('%Y')
            qtr = f"QTR{(date.month - 1) // 3 + 1}"
            filename = f"master.{date.strftime('%Y%m%d')}.idx"
            url = f"{self.base_url}/edgar/daily-index/{year}/{qtr}/{filename}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Failed to download daily index: {str(e)}")
            return None
            
    def parse_index_file(self, content, target_forms=None):
        if not content:
            return []
            
        filings = []
        current_filing = None
        
        for line in content.split('\n'):
            if not line.strip():
                continue
                
            if len(line) > 100:
                form_type = line[62:74].strip()
                company_name = line[0:62].strip()
                file_name = line[74:86].strip()
                date = line[86:98].strip()
                
                if target_forms and form_type not in target_forms:
                    continue
                    
                filing = {
                    'form_type': form_type,
                    'company_name': company_name,
                    'file_name': file_name,
                    'date': date,
                    'url': None
                }
                current_filing = filing
                filings.append(filing)
                
            elif line.startswith('edgar/data/'):
                if current_filing:
                    current_filing['url'] = line.strip()
                    
        return filings
        
    def download_filing(self, filing, output_dir):
        try:
            if not filing['url']:
                return False
                
            url = f"{self.base_url}/{filing['url']}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            form_dir = output_dir / filing['form_type']
            form_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = form_dir / f"{filing['file_name']}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download filing {filing['file_name']}: {str(e)}")
            return False
            
    def process_daily_filings(self, date, output_dir, target_forms=None):
        index_content = self.download_daily_index(date)
        if not index_content:
            return False
            
        filings = self.parse_index_file(index_content, target_forms)
        if not filings:
            self.logger.warning(f"No filings found for date: {date.strftime('%Y%m%d')}")
            return False
            
        date_dir = output_dir / date.strftime('%Y%m%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        for filing in filings:
            if self.download_filing(filing, date_dir):
                success_count += 1
                
        self.logger.info(f"Downloaded {success_count} of {len(filings)} filings for {date.strftime('%Y%m%d')}")
        return True
        
def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    downloader = SECDownloader()
    target_forms = ['8-K', 'S-4', 'PREM14A', 'SC14D9', '425']
    output_dir = Path('data/raw')
    
    yesterday = datetime.now().date() - timedelta(days=1)
    downloader.process_daily_filings(yesterday, output_dir, target_forms)
    
if __name__ == '__main__':
    main() 