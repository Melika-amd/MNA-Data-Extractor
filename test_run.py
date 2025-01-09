import os
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from src.download_filings import SECDownloader
from src.process_filings import FilingProcessor

def test_system():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    data_dir = Path('data')
    raw_dir = data_dir / 'raw'
    processed_dir = data_dir / 'processed'
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    test_date = datetime.strptime('20250110', '%Y%m%d').date()
    print(f"\n1. Checking SEC filings for date: {test_date.strftime('%Y%m%d')}")
    print("-" * 50)
    
    downloader = SECDownloader()
    
    target_forms = ['8-K', 'S-4', 'PREM14A', 'SC14D9', '425']
    
    date_dir = raw_dir / test_date.strftime('%Y%m%d')
    if date_dir.exists():
        print("\nFound existing downloaded files:")
        for form_type in target_forms:
            form_dir = date_dir / form_type
            if form_dir.exists():
                file_count = len(list(form_dir.glob('*.txt')))
                if file_count > 0:
                    print(f"{form_type}: {file_count} files")
    else:
        print("\nDownloading new files...")
        downloader.process_daily_filings(test_date, raw_dir, target_forms)
        
    print("\n2. Processing filings")
    print("-" * 50)
    
    processor = FilingProcessor()
    ma_data = processor.process_daily_filings(test_date)
    
    if ma_data is None or ma_data.empty:
        print("\nNo M&A data was found for this date")
        return
        
    print(f"\nFound {len(ma_data)} M&A-related filings")
    
    print("\nSample of extracted data:")
    print(ma_data.head().to_string())
    
    print("\nM&A filings by form type:")
    print(ma_data['form_type'].value_counts())
    
    print("\nTransaction value statistics:")
    print(ma_data['transaction_value'].describe())
    
if __name__ == '__main__':
    test_system() 