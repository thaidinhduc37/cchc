# server/services/vector_rag/web_processor.py
"""
Web Processor - Tối ưu cho 11 thủ tục xuất nhập cảnh
"""
import os
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup
import re

from services.vector_rag.rag_config import config, XUATNHAPCANH_WEB_PROCEDURES

logger = logging.getLogger(__name__)

class WebProcessor:
    """Web Processor cho 11 thủ tục xuất nhập cảnh"""
    
    def __init__(self):
        self.base_url = config.web_base_url
        self.cache_ttl = config.web_cache_ttl
        self.procedures = XUATNHAPCANH_WEB_PROCEDURES
        
        # 🎯 12 sections quan trọng theo thứ tự ưu tiên
        self.important_sections = [
            "Mã thủ tục", "Tên thủ tục", 
            "Yêu cầu - điều kiện", "Thành phần hồ sơ", 
            "Trình tự thực hiện", "Cách thức thực hiện",
            "Thời hạn giải quyết", "Phí", "Lệ Phí",
            "Cơ quan thực hiện", "Căn cứ pháp lý", "Kết quả thực hiện"
        ]
        
        # Cache
        self.cache = {}
        self.cache_file = os.path.join(config.web_cache_path, "web_cache.json")
        self._load_cache()
        
        logger.info(f"🔧 WebProcessor: {len(self.procedures)} procedures, {len(self.important_sections)} sections")
    
    def _load_cache(self):
        """Load cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"📂 Loaded {len(self.cache)} cached procedures")
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Save cache"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")
    
    def _is_cache_valid(self, timestamp: str) -> bool:
        """Check cache validity"""
        try:
            cache_time = datetime.fromisoformat(timestamp)
            return datetime.now() - cache_time < timedelta(seconds=self.cache_ttl)
        except:
            return False
    
    async def fetch_procedure(self, procedure_code: str) -> Optional[Dict[str, Any]]:
        """Fetch single procedure data"""
        cache_key = f"procedure_{procedure_code}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if self._is_cache_valid(cached_data.get('timestamp', '')):
                logger.debug(f"📋 Cache hit: {procedure_code}")
                return cached_data['data']
        
        # Fetch from web
        logger.info(f"🌐 Fetching: {procedure_code}")
        url = f"{self.base_url}/bocongan/bothutuc/tthc?matt={procedure_code}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        data = self._extract_procedure_data(html, procedure_code)
                        
                        if data and len(data.get('sections', {})) >= 3:
                            # Cache result
                            self.cache[cache_key] = {
                                'data': data,
                                'timestamp': datetime.now().isoformat(),
                                'url': url
                            }
                            self._save_cache()
                            
                            logger.info(f"✅ Extracted: {data.get('title', procedure_code)} ({len(data['sections'])} sections)")
                            return data
                        else:
                            logger.warning(f"⚠️ Poor extraction for {procedure_code}")
                    else:
                        logger.warning(f"HTTP {response.status} for {procedure_code}")
                        
        except Exception as e:
            logger.error(f"Fetch error for {procedure_code}: {e}")
        
        return None
    
    def _extract_procedure_data(self, html: str, code: str) -> Optional[Dict[str, Any]]:
        """Extract procedure data from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts and styles
            for tag in soup(["script", "style"]):
                tag.decompose()
            
            text = soup.get_text()
            
            # Base data
            data = {
                'code': code,
                'title': self._extract_title(soup),
                'sections': {},
                'extracted_at': datetime.now().isoformat(),
                'content_type': 'web_procedure'
            }
            
            # Extract each important section
            for section_name in self.important_sections:
                section_content = self._extract_section(text, section_name)
                if section_content:
                    data['sections'][section_name] = section_content
            
            return data if len(data['sections']) >= 3 else None
            
        except Exception as e:
            logger.error(f"Extraction error for {code}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract procedure title"""
        # Try common title selectors
        for selector in ['h1', 'h2', '.title', '.procedure-title']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                title = element.get_text(strip=True)
                if 20 <= len(title) <= 200:
                    return title
        
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Clean title
            title = re.sub(r'\s*[-|]\s*(?:Cổng|Dịch vụ|Bộ).*$', '', title)
            return title
        
        return "Thủ tục không xác định"
    
    def _extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract specific section content"""
        
        # Section patterns cho từng loại
        section_patterns = {
            "Mã thủ tục": [
                r'(?:Mã\s+thủ\s+tục|Mã\s+số)[\s:]*([A-Z0-9]{4,6})',
            ],
            "Cơ quan thực hiện": [
                r'(?:Cơ\s+quan\s+(?:thực\s+hiện|có\s+thẩm\s+quyền))[\s:]*([^\n]+?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Yêu cầu - điều kiện": [
                r'(?:Yêu\s+cầu[\s\-]*điều\s+kiện|Điều\s+kiện|Đối\s+tượng)[\s:]*\n(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Thành phần hồ sơ": [
                r'(?:Thành\s+phần\s+hồ\s+sơ|Hồ\s+sơ\s+gồm)[\s:]*\n(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Trình tự thực hiện": [
                r'(?:Trình\s+tự\s+(?:thực\s+hiện|làm)|Quy\s+trình)[\s:]*\n(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Cách thức thực hiện": [
                r'(?:Cách\s+thức\s+(?:thực\s+hiện|tiếp\s+nhận))[\s:]*\n(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Thời hạn giải quyết": [
                r'(?:Thời\s+(?:hạn|gian)\s+(?:giải\s+quyết|xử\s+lý))[\s:]*([^\n]+)',
                r'(\d+\s*(?:ngày|tháng|tuần)\s*(?:làm\s+việc)?)',
            ],
            "Phí": [
                r'(?:Chi\s+phí|Mức\s+phí|Phí\s+dịch\s+vụ)[\s:]*([^\n]+)',
                r'(\d+(?:[.,]\d{3})*\s*(?:đồng|VNĐ|vnđ)|miễn\s*phí)',
            ],
            "Lệ Phí": [
                r'(?:Lệ\s+phí)[\s:]*([^\n]+)',
                r'(\d+(?:[.,]\d{3})*\s*(?:đồng|VNĐ|vnđ)|miễn\s*phí)',
            ],
            "Căn cứ pháp lý": [
                r'(?:Căn\s+cứ\s+pháp\s+lý|Cơ\s+sở\s+pháp\s+lý)[\s:]*\n(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{3,}|$)',
            ],
            "Kết quả thực hiện": [
                r'(?:Kết\s+quả\s+(?:thực\s+hiện|giải\s+quyết)|Sản\s+phẩm)[\s:]*([^\n]+)',
            ]
        }
        
        # Try patterns for this section
        patterns = section_patterns.get(section_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1) if match.groups() else match.group(0)
                content = self._clean_content(content)
                
                if len(content) >= 15:  # Minimum meaningful content
                    return content
        
        return None
    
    def _clean_content(self, content: str) -> str:
        """Clean extracted content"""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove common noise
        noise_patterns = [
            r'Hiển thị.*?$',
            r'Copyright.*?$',
            r'^\s*[.,-]+\s*',
        ]
        
        for pattern in noise_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    async def search_procedures(self, query: str) -> List[Dict[str, Any]]:
        """🎯 Search procedures với intent-aware filtering"""
        results = []
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w{3,}\b', query_lower))
        
        # 🎯 Detect search intent để filter sections
        search_intent = self._detect_search_intent(query_lower)
        
        # Score all procedures
        scored_procedures = []
        
        for procedure_name, code in self.procedures.items():
            proc_words = set(re.findall(r'\b\w{3,}\b', procedure_name.lower()))
            
            # Calculate relevance
            intersection = query_words & proc_words
            if len(intersection) > 0:
                jaccard = len(intersection) / len(query_words | proc_words)
                coverage = len(intersection) / len(proc_words)
                relevance = (jaccard + coverage) / 2
                
                scored_procedures.append({
                    'name': procedure_name,
                    'code': code,
                    'relevance_score': relevance
                })
        
        # Sort by relevance and take top 3
        scored_procedures.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        for proc_info in scored_procedures[:3]:
            if proc_info['relevance_score'] >= 0.1:
                try:
                    procedure_data = await self.fetch_procedure(proc_info['code'])
                    if procedure_data:
                        procedure_data['relevance_score'] = proc_info['relevance_score']
                        procedure_data['search_intent'] = search_intent
                        results.append(procedure_data)
                except Exception as e:
                    logger.warning(f"Search fetch failed for {proc_info['code']}: {e}")
        
        logger.info(f"✅ Search found {len(results)} procedures for: {query}")
        return results
    
    def _detect_search_intent(self, query: str) -> Dict[str, Any]:
        """🎯 Detect search intent để tối ưu sections"""
        intent_patterns = {
            'requirements': ['điều kiện', 'yêu cầu', 'đối tượng', 'ai được'],
            'documents': ['hồ sơ', 'giấy tờ', 'tài liệu', 'cần gì'],
            'process': ['trình tự', 'quy trình', 'các bước', 'làm thế nào'],
            'fee': ['phí', 'lệ phí', 'chi phí', 'bao nhiêu tiền'],
            'time': ['thời gian', 'thời hạn', 'bao lâu', 'mất bao nhiêu'],
            'agency': ['cơ quan', 'nơi nào', 'ở đâu'],
            'result': ['được cấp', 'kết quả', 'nhận được gì']
        }
        
        detected_intents = []
        for intent, keywords in intent_patterns.items():
            if any(keyword in query for keyword in keywords):
                detected_intents.append(intent)
        
        return {
            'primary_intent': detected_intents[0] if detected_intents else 'general',
            'all_intents': detected_intents
        }
    
    def format_for_rag(self, procedure_data: Dict) -> str:
        """Format procedure data for RAG với intent filtering"""
        sections = []
        
        # Title
        if procedure_data.get('title'):
            sections.append(f"# {procedure_data['title']}")
        
        # 🎯 Filter sections based on search intent
        search_intent = procedure_data.get('search_intent', {})
        primary_intent = search_intent.get('primary_intent', 'general')
        
        # Section priority mapping
        intent_section_mapping = {
            'requirements': ['Yêu cầu - điều kiện'],
            'documents': ['Thành phần hồ sơ'],
            'process': ['Trình tự thực hiện', 'Cách thức thực hiện'],
            'fee': ['Phí', 'Lệ Phí'],
            'time': ['Thời hạn giải quyết'],
            'agency': ['Cơ quan thực hiện'],
            'result': ['Kết quả thực hiện']
        }
        
        # Get priority sections for this intent
        priority_sections = intent_section_mapping.get(primary_intent, [])
        
        # Add priority sections first
        added_sections = set()
        for section_name in priority_sections:
            content = procedure_data.get('sections', {}).get(section_name)
            if content and content.strip():
                sections.append(f"\n## {section_name}")
                sections.append(content.strip())
                added_sections.add(section_name)
        
        # Add remaining important sections
        for section_name in self.important_sections:
            if section_name not in added_sections:
                content = procedure_data.get('sections', {}).get(section_name)
                if content and content.strip():
                    sections.append(f"\n## {section_name}")
                    sections.append(content.strip())
        
        # Metadata
        sections.append(f"\n## Thông tin bổ sung")
        sections.append(f"Mã thủ tục: {procedure_data.get('code', 'N/A')}")
        sections.append(f"Nguồn: Cổng dịch vụ công Bộ Công an")
        
        return '\n'.join(sections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'total_procedures': len(self.procedures),
            'cached_procedures': len(self.cache),
            'important_sections': len(self.important_sections),
            'cache_ttl_hours': self.cache_ttl / 3600,
            'base_url': self.base_url
        }
    
    def clear_cache(self):
        """Clear cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("🗑️ Web cache cleared")