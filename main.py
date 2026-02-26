import os
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from google.cloud import firestore
import time
import logging

app = Flask(__name__)
db = firestore.Client()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JinPingMeiScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://www.jinpingmei23.tw/"

    def fetch_page(self, url):
        try:
            response = self.session.get(url, timeout=10)
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_name(self, text):
        match = re.search(r'^([\u4e00-\u9fff]+)', text)
        return match.group(1) if match else text.strip()

    def extract_price(self, text):
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0

    def generate_external_id(self, name, area):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{area[:3]}-{name}-{timestamp}"

    def scrape_character_cards(self):
        soup = self.fetch_page(self.base_url)
        if not soup:
            return []

        characters = []
        
        cards = soup.find_all('div', class_=re.compile('card|item|character'))
        
        for card in cards:
            try:
                name_elem = card.find(['h1', 'h2', 'h3', 'span', 'div'], class_=re.compile('name|title'))
                age_elem = card.find(['span', 'div'], class_=re.compile('age'))
                height_elem = card.find(['span', 'div'], class_=re.compile('height'))
                price_elem = card.find(['span', 'div'], class_=re.compile('price|cost'))
                area_elem = card.find(['span', 'div'], class_=re.compile('area|location'))
                img_elem = card.find('img')
                
                name = self.extract_name(name_elem.get_text() if name_elem else 'Unknown')
                age = age_elem.get_text().strip() if age_elem else 'N/A'
                height = height_elem.get_text().strip() if height_elem else 'N/A'
                price = price_elem.get_text().strip() if price_elem else '0'
                area = area_elem.get_text().strip() if area_elem else '未知'
                photo_url = img_elem['src'] if img_elem else ''
                
                external_id = self.generate_external_id(name, area)
                
                character = {
                    'externalId': external_id,
                    'name': name,
                    'age': age,
                    'height': height,
                    'price': self.extract_price(price),
                    'area': area,
                    'photo_main': photo_url,
                    'photo_secondary': '',
                    'service': '',
                    'more': '',
                    'status': 'active',
                    'updatedAt': datetime.now().isoformat(),
                    'createdAt': datetime.now().isoformat()
                }
                
                characters.append(character)
                
            except Exception as e:
                logger.warning(f"Failed to parse card: {e}")
                continue
        
        return characters

    def save_to_firestore(self, characters):
        stats = {'inserted': 0, 'updated': 0, 'deactivated': 0}
        
        for char in characters:
            ext_id = char['externalId']
            doc_ref = db.collection('persons').document(ext_id)
            doc = doc_ref.get()
            
            if doc.exists:
                if self.has_changed(doc.to_dict(), char):
                    doc_ref.update(char)
                    stats['updated'] += 1
                    logger.info(f"Updated: {ext_id}")
                else:
                    doc_ref.update({'updatedAt': datetime.now().isoformat()})
            else:
                doc_ref.set(char)
                stats['inserted'] += 1
                logger.info(f"Inserted: {ext_id}")
        
        self.deactivate_old_records()
        return stats

    def deactivate_old_records(self):
        now = datetime.now()
        seven_days_ago = datetime.fromisoformat(
            (now.timestamp() - 604800).__str__()
        )
        
        docs = db.collection('persons').where(
            'updatedAt', '<', seven_days_ago.isoformat()
        ).where('status', '==', 'active').stream()
        
        for doc in docs:
            doc.reference.update({
                'status': 'inactive',
                'deactivatedAt': now.isoformat(),
                'reason': 'auto_deactivated_7days'
            })
            logger.info(f"Deactivated: {doc.id}")

    def has_changed(self, old_dict, new_dict):
        return (
            old_dict.get('price') != new_dict['price'] or
            old_dict.get('service') != new_dict['service'] or
            old_dict.get('photo_main') != new_dict['photo_main'] or
            old_dict.get('more') != new_dict['more'] or
            old_dict.get('area') != new_dict['area']
        )

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    try:
        scraper = JinPingMeiScraper()
        characters = scraper.scrape_character_cards()
        stats = scraper.save_to_firestore(characters)
        
        return jsonify({
            'success': True,
            'message': 'Scrape completed',
            'stats': stats,
            'total_characters': len(characters)
        }), 200
    except Exception as e:
        logger.error(f"Error during scrape: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
