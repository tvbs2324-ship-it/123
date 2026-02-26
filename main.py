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
    
    def get_all_categories(self):
        """Get all category URLs by parsing the main page"""
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links that contain category information
            categories = []
            
            # Look for all a tags and extract those with proper hrefs
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Filter for location pages (contains location names)
                if href and '/' in href and any(keyword in text for keyword in ['定點', '外約']):
                    full_url = href if href.startswith('http') else self.base_url + href
                    categories.append({'name': text, 'url': full_url})
            
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def extract_girl_info(self, text, location_name):
        """Extract girl information from page text using text parsing"""
        girls = []
        
        # Pattern to match girl entries
        # Format: Name (Country) Age/Height/Weight/Cup ... 💰price
        # Example: 周語晨(越) 20Y/164/43/真E
        pattern = r'(中文|[\u4e00-\u9fa5]{2,4})(\(\w+\))?\s+(\d{1,2})Y/(\d{3})/(\d{2})/([真])([A-E])[^\n]*'
        
        # Split by girl entries and parse each
        lines = text.split('\n')
        current_girl = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Try to find girl name pattern
            if re.search(r'[一-\u9fa5]{2,4}\(\w+\)\s+\d{1,2}Y/\d{3}/\d{2}', line):
                # Found a new girl
                if current_girl:
                    girls.append(current_girl)
                
                # Parse girl info
                match = re.search(r'([一-\u9fa5]{2,4})(\(\w+\))?\s+(\d{1,2})Y/(\d{3})/(\d{2})/([^\s/]+)', line)
                if match:
                    name = match.group(1)
                    age = match.group(3)
                    height = match.group(4)
                    weight = match.group(5)
                    cup = match.group(6)[-1] if len(match.group(6)) > 0 else ''
                    
                    current_girl = {
                        '分類': location_name,
                        '姓名': name,
                        '身高': height,
                        '体重': weight,
                        '罩杖': cup,
                        '年齢': age,
                        '服務項目': '',
                        '40分鐘成一事約': '',
                        '60分鐘成一事約': '',
                        '抶取時間': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Look ahead for service and price info
                    for j in range(i+1, min(i+30, len(lines))):
                        next_line = lines[j].strip()
                        
                        # Look for prices
                        if '✔' in next_line or 'Ἆ' in next_line or '1s/' in next_line:
                            if '40' in next_line:
                                current_girl['40分鐘成一事約'] = re.findall(r'\d{4}', next_line)[0] if re.findall(r'\d{4}', next_line) else ''
                            if '50' in next_line:
                                current_girl['60分鐘成一事約'] = re.findall(r'\d{4}', next_line)[0] if re.findall(r'\d{4}', next_line) else ''
                        
                        # Look for service line
                        if '服務' in next_line or '舌' in next_line or '事' in next_line:
                            current_girl['服務項目'] = next_line[:100]
                            break
        
        if current_girl:
            girls.append(current_girl)
        
        return girls
    
    def scrape_category(self, category):
        """Scrape a single category page"""
        try:
            print(f"Scraping: {category['name']}")
            response = self.session.get(category['url'])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get all text content
            text = soup.get_text()
            
            # Extract girl info
            girls = self.extract_girl_info(text, category['name'])
            self.all_data.extend(girls)
            
            print(f" Found {len(girls)} girls")
            time.sleep(1)  # Be respectful with requests
            
        except Exception as e:
            print(f"Error scraping {category['name']}: {e}")
    
    def save_to_csv(self, filename='scraped_data.csv'):
        """Save data to CSV file"""
        if not self.all_data:
            print("No data to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['分類', '姓名', '身高', '体重', '罩杖', '年齢', '服務項目', '40分鐘成一事約', '60分鐘成一事約', '抶取時間']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_data)
        
        print(f"\nData saved to {filename}")
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
        
        self.save_to_csv()
        print("\nScraping completed!")

if __name__ == '__main__':
    scraper = JinPingMeiScraper()
    scraper.run()
