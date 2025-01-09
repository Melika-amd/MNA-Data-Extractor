import os
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from src.parsers.form_8k import Form8KParser
from src.parsers.form_425 import Form425Parser
from src.parsers.form_s4 import FormS4Parser

class FilingProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.raw_dir = Path('data/raw')
        self.processed_dir = Path('data/processed')
        
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.parsers = {
            '8-K': Form8KParser(),
            '425': Form425Parser(),
            'S-4': FormS4Parser()
        }
        
    def process_daily_filings(self, date):
        try:
            date_str = date.strftime('%Y%m%d')
            date_dir = self.raw_dir / date_str
            
            if not date_dir.exists():
                self.logger.warning(f"No filings found for date: {date_str}")
                return None
                
            ma_data = []
            
            for form_type, parser in self.parsers.items():
                form_dir = date_dir / form_type
                if not form_dir.exists():
                    continue
                    
                filings = list(form_dir.glob('*.txt'))
                if filings:
                    desc = f"Processing {form_type} filings"
                    for filing_path in tqdm(filings, desc=desc):
                        try:
                            result = parser.parse_filing(filing_path)
                            if result and isinstance(result, dict):
                                result['date'] = date
                                result['file_path'] = str(filing_path)
                                result['form_type'] = form_type
                                ma_data.append(result)
                        except Exception as e:
                            self.logger.error(f"Error parsing filing {filing_path}: {str(e)}")
                            continue
                            
            if ma_data:
                df = pd.DataFrame(ma_data)
                
                output_file = self.processed_dir / f"ma_data_{date_str}.parquet"
                df.to_parquet(output_file)
                
                self.logger.info(f"\nFound {len(df)} M&A filings:")
                for form in df['form_type'].unique():
                    count = len(df[df['form_type'] == form])
                    self.logger.info(f"- {form}: {count} filings")
                    
                if 'transaction_value' in df.columns:
                    value_stats = df['transaction_value'].describe()
                    self.logger.info("\nTransaction Value Statistics:")
                    self.logger.info(f"Count: {value_stats['count']}")
                    self.logger.info(f"Mean: ${value_stats['mean']:,.2f}")
                    self.logger.info(f"Std: ${value_stats['std']:,.2f}")
                    self.logger.info(f"Min: ${value_stats['min']:,.2f}")
                    self.logger.info(f"Max: ${value_stats['max']:,.2f}")
                
                return df
                
            self.logger.info("No M&A data was found for this date")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error processing filings for {date}: {str(e)}")
            return None

def main():
    processor = FilingProcessor()
    
    date = datetime.now()
    processor.process_daily_filings(date)

if __name__ == "__main__":
    main() 