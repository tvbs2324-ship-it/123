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
        """获取所有分类链接"""
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            menu = soup.find('nav', id='menu')
            categories = []
            if menu:
                links = menu.find_all('a')
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href and href != '/' and '定點' in text or '外約' in text:
                        full_url = self.base_url + href if href.startswith('/') else href
                        categories.append({'name': text, 'url': full_url})
            return categories
        except Exception as e:
            print(f"获取分类失败: {e}")
            return []
    
    def extract_role_info(self, soup, category_name):
        """从页面提取所有角色信息"""
        roles = []
        # 查找所有图片块
        images = soup.find_all('img')
        text_content = soup.get_text()
        
        # 使用正则表达式匹配角色信息模式
        # 匹配名字和基本信息 (身高.罩杯.年龄)
        pattern = r'([\u4e00-\u9fa5]{2,4})\s*[\n\s]*(\d{3})\.(\d{2})\.(\w)\.(\d{2})Y?'
        matches = re.finditer(pattern, text_content)
        
        for match in matches:
            name = match.group(1)
            height = match.group(2)
            weight = match.group(3)
            cup = match.group(4)
            age = match.group(5)
            
            # 提取该角色后面的服务信息
            start_pos = match.end()
            next_match_pos = text_content.find('💰', start_pos)
            if next_match_pos == -1:
                next_match_pos = start_pos + 500
            
            service_text = text_content[start_pos:next_match_pos]
            
            # 提取服务项目
            service_line = ''
            for line in service_text.split('\n'):
                if '服務' in line or '舌吻' in line or '按摩' in line:
                    service_line = line.strip()
                    break
            
            # 提取价格
            prices = re.findall(r'💰?\s*(\d+)分.*?(\d{4})', text_content[start_pos:next_match_pos+200])
            price_40 = prices[0][1] if len(prices) > 0 else ''
            price_60 = prices[1][1] if len(prices) > 1 else ''
            
            role = {
                '分类': category_name,
                '姓名': name,
                '身高': height,
                '体重': weight,
                '罩杯': cup,
                '年龄': age,
                '服务项目': service_line[:100],
                '40分钟价格': price_40,
                '60分钟价格': price_60,
                '抓取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            roles.append(role)
        
        return roles
    
    def scrape_category(self, category):
        """爬取单个分类的所有数据"""
        try:
            print(f"正在爬取: {category['name']}")
            response = self.session.get(category['url'])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            roles = self.extract_role_info(soup, category['name'])
            self.all_data.extend(roles)
            print(f"  找到 {len(roles)} 个角色")
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"爬取 {category['name']} 失败: {e}")
    
    def save_to_csv(self, filename='scraped_data.csv'):
        """保存数据到CSV"""
        if not self.all_data:
            print("没有数据可保存")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['分类', '姓名', '身高', '体重', '罩杯', '年龄', '服务项目', '40分钟价格', '60分钟价格', '抓取时间']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_data)
        
        print(f"\n数据已保存到 {filename}")
        print(f"总共爬取 {len(self.all_data)} 条记录")
    
    def run(self):
        """运行完整爬虫"""
        print("开始爬取金瓶梅网站...")
        print("="*50)
        
        # 获取所有分类
        categories = self.get_all_categories()
        print(f"找到 {len(categories)} 个分类\n")
        
        # 爬取每个分类
        for i, category in enumerate(categories, 1):
            print(f"[{i}/{len(categories)}] ", end='')
            self.scrape_category(category)
        
        # 保存数据
        self.save_to_csv()
        print("\n爬取完成！")

if __name__ == '__main__':
    scraper = JinPingMeiScraper()
    scraper.run()
