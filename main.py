import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime
import os

class JinPingMeiScraper:
    def __init__(self):
        self.base_url = "https://www.jinpingmei23.tw"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.all_data = []
        self.category_data = {}
    
    def get_all_categories(self):
        """Get all category URLs"""
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            categories = []
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and '/' in href and any(keyword in text for keyword in ['定點', '外約', '台妹']):
                    full_url = href if href.startswith('http') else self.base_url + href
                    # Clean category name for filename
                    safe_name = re.sub(r'[/\\:*?"<>|]', '-', text)
                    categories.append({'name': text, 'url': full_url, 'safe_name': safe_name})
            
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def extract_girl_info(self, text, location_name):
        """Extract girl information from page text"""
        girls = []
        
        # Split by common delimiters and process line by line
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for lines with girl name pattern: 2-4 Chinese chars, optionally (country), age, height, weight, cup
            # More flexible pattern to catch different formats
            match = re.search(r'([一-龥]{2,4})\s*(?:\(\w+\))?\s+(\d{1,2})Y/(\d{3})/(\d{2})(?:/|\.)([\u771f]?)([A-E]+)', line)
            
            if match:
                name = match.group(1)
                age = match.group(2)
                height = match.group(3)
                weight = match.group(4)
                cup = match.group(6) if match.group(6) else match.group(5)[-1] if match.group(5) else ''
                
                girl = {
                    '分類': location_name,
                    '姓名': name,
                    '身高': height,
                    '체重': weight,
                    '罩杖': cup,
                    '年齢': age,
                    '服務項目': '',
                    '40分鐘成一事約': '',
                    '60分鐘成一事約': '',
                    '抶取時間': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Look ahead for prices and services
                for j in range(i+1, min(i+50, len(lines))):
                    next_line = lines[j].strip()
                    
                    # Extract prices (look for 1s/40/3000 pattern or similar)
                    if '/40/' in next_line or '1s/40' in next_line:
                        prices = re.findall(r'\d{4}', next_line)
                        if prices:
                            girl['40分鐘成一事約'] = prices[0]
                    
                    if '/50/' in next_line or '/60/' in next_line or '1s/50' in next_line:
                        prices = re.findall(r'\d{4}', next_line)
                        if prices:
                            girl['60分鐘成一事約'] = prices[-1] if len(prices) > 1 else prices[0]
                    
                    # Stop looking if we hit another girl or end marker
                    if re.search(r'[一-龥]{2,4}\s*(?:\(\w+\))?\s+\d{1,2}Y/\d{3}/\d{2}', next_line) and next_line != line:
                        break
                
                girls.append(girl)
            
            i += 1
        
        return girls
    
    def scrape_category(self, category):
        """Scrape a single category page"""
        try:
            print(f"Scraping: {category['name']}", end='... ')
            response = self.session.get(category['url'], timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            text = soup.get_text()
            girls = self.extract_girl_info(text, category['name'])
            
            # Store in both overall and category-specific lists
            self.all_data.extend(girls)
            self.category_data[category['safe_name']] = girls
            
            print(f"Found {len(girls)} girls")
            time.sleep(0.5)  # Be respectful
            
        except Exception as e:
            print(f"Error: {e}")
    
    def save_to_csv_by_category(self):
        """Save data to individual CSV files by category"""
        fieldnames = ['分類', '姓名', '身高', '体重', '罩杖', '年齢', '服務項目', '40分鐘成一事約', '60分鐘成一事約', '抶取時間']
        
        for safe_name, data in self.category_data.items():
            if data:  # Only save if there's data
                filename = f"{safe_name}.csv"
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                print(f"Saved: {filename} ({len(data)} records)")
    
    def save_to_csv_all(self, filename='scraped_data_all.csv'):
        """Save all data to a single CSV"""
        if not self.all_data:
            print("No data to save")
            return
        
        fieldnames = ['分類', '姓名', '身高', '体重', '罩杖', '年齢', '服務項目', '40分鐘成一事約', '60分鐘成一事約', '抶取時間']
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_data)
        
        print(f"\nAll data saved to {filename}")
        print(f"Total records: {len(self.all_data)}")
    
    def run(self):
        """Run the complete scraper"""
        print("Starting JinPingMei scraper...")
        print("="*50)
        
        categories = self.get_all_categories()
        print(f"Found {len(categories)} categories\n")
        
        for i, category in enumerate(categories, 1):
            print(f"[{i}/{len(categories)}] ", end='')
            self.scrape_category(category)
        
        # Save both individual and combined CSVs
        print("\n" + "="*50)
        print("Saving individual category CSVs...")
        self.save_to_csv_by_category()
        
        print("\nSaving combined CSV...")
        self.save_to_csv_all()
        
        print("\nScraping completed!")

if __name__ == '__main__':
    scraper = JinPingMeiScraper()
    scraper.run()
