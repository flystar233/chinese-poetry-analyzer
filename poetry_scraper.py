#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
古诗词牌谱爬虫脚本
用于从HTML网页中提取词牌名、作者和平仄信息
"""

import re
import csv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import os

class PoetryPatternScraper:
    """古诗词牌谱爬虫类"""
    
    def __init__(self):
        self.tone_pattern = re.compile(r'[○●⊙◎]+')  # 匹配平仄符号
        self.cipai_data = []
        
    def fetch_html_from_url(self, url: str) -> str:
        """
        从URL获取HTML内容
        
        Args:
            url: 网页URL
            
        Returns:
            HTML内容字符串
        """
        try:
            # 添加http://前缀
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            print(f"正在获取网页内容: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 尝试自动检测编码
            if response.encoding == 'ISO-8859-1':
                # 如果自动检测失败，尝试常见的中文编码
                encodings = ['gb2312', 'gbk', 'utf-8']
                for encoding in encodings:
                    try:
                        content = response.content.decode(encoding)
                        return content
                    except UnicodeDecodeError:
                        continue
            
            return response.text
            
        except requests.RequestException as e:
            print(f"网络请求失败: {e}")
            return ""
        except Exception as e:
            print(f"获取HTML内容时出错: {e}")
            return ""
    
    def parse_html_content(self, html_content: str) -> List[str]:
        """
        解析HTML内容，只提取平仄模式信息
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            平仄模式字符串列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取所有段落
        paragraphs = soup.find_all('p')
        
        tone_patterns = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            
            # 跳过空白段落
            if not text:
                continue
            
            # 检测平仄信息
            tone_lines = self._extract_tone_pattern(text)
            if tone_lines:
                for tone_line in tone_lines:
                    # 避免重复添加相同的平仄信息
                    if tone_line not in tone_patterns:
                        tone_patterns.append(tone_line)
        
        return tone_patterns
    

    
    def _extract_tone_pattern(self, text: str) -> List[str]:
        """提取平仄信息"""
        # 按行分割文本
        lines = text.split('\n')
        valid_patterns = []
        
        for line in lines:
            # 检查是否包含平仄符号且符号数量足够多
            tone_symbols = re.findall(r'[○●⊙◎]', line)
            if len(tone_symbols) >= 5:  # 至少5个平仄符号
                # 提取这一行的完整平仄信息
                # 移除其他字符，只保留平仄符号和空格/制表符
                clean_pattern = re.sub(r'[^○●⊙◎\s　]', '', line)
                clean_pattern = re.sub(r'\s+', ' ', clean_pattern.strip())
                if clean_pattern:
                    valid_patterns.append(clean_pattern)
        
        return valid_patterns
    
    def save_to_txt(self, tone_patterns: List[str], filename: str = 'tone_patterns.txt'):
        """将平仄模式保存到TXT文件"""
        if not tone_patterns:
            print("没有平仄模式可保存")
            return
        
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as txtfile:
            for i, pattern in enumerate(tone_patterns, 1):
                txtfile.write(f"{i:04d}: {pattern}\n")
        
        print(f"平仄模式已保存到: {filepath}")
        print(f"共保存 {len(tone_patterns)} 条平仄模式")
    

    
    def print_summary(self, tone_patterns: List[str]):
        """打印平仄模式摘要"""
        if not tone_patterns:
            print("没有提取到任何平仄模式")
            return
        
        print(f"\n{'='*50}")
        print(f"平仄模式提取摘要")
        print(f"{'='*50}")
        print(f"总共提取到: {len(tone_patterns)} 条平仄模式")
        
        # 统计字数分布
        char_counts = {}
        for pattern in tone_patterns:
            tone_chars = [char for char in pattern if char in '○●⊙◎']
            char_count = len(tone_chars)
            char_counts[char_count] = char_counts.get(char_count, 0) + 1
        
        print(f"\n字数分布:")
        for char_count in sorted(char_counts.keys())[:15]:  # 显示前15种字数
            count = char_counts[char_count]
            print(f"  {char_count}字: {count} 条")
        
        if len(char_counts) > 15:
            print(f"  ... 还有其他字数的模式")
        
        print(f"\n前10条平仄模式:")
        for i, pattern in enumerate(tone_patterns[:10], 1):
            tone_chars = [char for char in pattern if char in '○●⊙◎']
            char_count = len(tone_chars)
            print(f"  【{i:04d}】 ({char_count}字) {pattern[:60]}{'...' if len(pattern) > 60 else ''}")


def main():
    """主函数"""
    # 创建爬虫实例
    scraper = PoetryPatternScraper()
    
    # 存储所有提取的平仄模式
    all_tone_patterns = []
    
    # 批量爬取从004到043的所有页面
    start_page = 4
    end_page = 43
    
    print(f"开始批量爬取从{start_page:03d}.htm到{end_page:03d}.htm的页面...")
    print("只提取平仄模式信息，忽略词牌名和作者...")
    
    for page_num in range(start_page, end_page + 1):
        # 生成URL
        url = f"http://www.guoxue123.com/jijijibu/0401/00qdcp/{page_num:03d}.htm"
        
        print(f"\n正在处理第{page_num:03d}页: {url}")
        
        # 从URL获取HTML内容
        html_content = scraper.fetch_html_from_url(url)
        
        if not html_content:
            print(f"无法获取第{page_num:03d}页内容，跳过...")
            continue
        
        # 解析HTML内容，只获取平仄模式
        page_patterns = scraper.parse_html_content(html_content)
        
        if page_patterns:
            print(f"第{page_num:03d}页提取到{len(page_patterns)}条平仄模式")
            all_tone_patterns.extend(page_patterns)
        else:
            print(f"第{page_num:03d}页未提取到平仄模式")
        
        # 添加延迟以避免过于频繁的请求
        import time
        time.sleep(1)  # 1秒延迟
    
    # 打印总体摘要
    print(f"\n{'='*60}")
    print("批量爬取完成！")
    scraper.print_summary(all_tone_patterns)
    
    # 保存数据
    if all_tone_patterns:
        scraper.save_to_txt(all_tone_patterns, 'tone_patterns_all_pages.txt')
    else:
        print("未提取到任何平仄模式，请检查HTML格式或解析规则")


if __name__ == "__main__":
    main()