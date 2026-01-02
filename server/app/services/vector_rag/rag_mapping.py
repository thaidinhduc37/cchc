# services/vector_rag/rag_mapping.py
"""
RAG MAPPING - Chuyên ngành Xuất nhập cảnh
🎯 Dựa trên Luật 49/2019/QH14 - Mapping intent → vector search optimization
🚀 rag_engine → rag_mapping → vector_store (optimized search)
📋 Hardcode mapping cho domain xuất nhập cảnh
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class XuatNhapCanhMapping:
    """Mapping chuyên ngành cho xuất nhập cảnh - Luật 49/2019"""
    
    def __init__(self):
        # CORE: Intent mappings
        self.intent_mappings = self._build_intent_mappings()
        
        # CORE: Query pattern shortcuts  
        self.query_shortcuts = self._build_query_shortcuts()
        
        # CORE: Article-specific targeting
        self.article_targets = self._build_article_targets()
        
        # CORE: Keyword boost rules
        self.keyword_boost_rules = self._build_keyword_boosts()
        
        # CORE: Search strategy per intent
        self.search_strategies = self._build_search_strategies()
        
        # Stats
        self.stats = {
            'mapping_requests': 0,
            'intent_hits': 0,
            'pattern_hits': 0, 
            'article_hits': 0,
            'keyword_boosts': 0
        }
        
        logger.info("🎯 XuatNhapCanhMapping initialized - Luật 49/2019")
    
    def get_vector_search_config(self, query: str, intent_analysis: dict, 
                            unified_context: dict = None) -> Dict[str, Any]:
        """
        FIXED: Ensure always return valid config, never None
        """
        self.stats['mapping_requests'] += 1
        
        # FIXED: Default config - ALWAYS return valid dict
        search_config = {
            'method': 'standard',
            'target_articles': [],
            'boost_keywords': [],
            'search_strategy': 'balanced',
            'confidence_multiplier': 1.0,
            'filter_content_types': [],
            'priority_chunks': [],
            'threshold_adjustment': 0.0,
            'k_multiplier': 1.0,
            'debug_info': {},
            # NEW: Ensure all required keys exist
            'expected_law_unit': None,
            'law_unit_filter': None,
            'short_content_boost': 1.0
        }
        
        mapping_applied = False
        
        # STEP 1: Intent-based mapping với null safety
        try:
            if intent_analysis and isinstance(intent_analysis, dict):
                intent_config = self._map_by_intent(intent_analysis)
                if intent_config and isinstance(intent_config, dict):
                    search_config.update(intent_config)
                    search_config['method'] = 'intent_mapping'
                    self.stats['intent_hits'] += 1
                    mapping_applied = True
        except Exception as e:
            logger.warning(f"Intent mapping failed: {e}")
        
        # STEP 2: Query pattern shortcuts với exception handling
        try:
            pattern_config = self._map_by_query_patterns(query)
            if pattern_config and isinstance(pattern_config, dict):
                search_config = self._merge_configs(search_config, pattern_config)
                search_config['method'] = 'pattern_shortcut'
                self.stats['pattern_hits'] += 1
                mapping_applied = True
        except Exception as e:
            logger.warning(f"Pattern mapping failed: {e}")
        
        # STEP 3: Article-specific targeting với error handling
        try:
            article_config = self._map_by_articles(query)
            if article_config and isinstance(article_config, dict):
                search_config = self._merge_configs(search_config, article_config)
                search_config['method'] = 'article_targeting'
                self.stats['article_hits'] += 1
                mapping_applied = True
        except Exception as e:
            logger.warning(f"Article mapping failed: {e}")
        
        # STEP 4: Keyword boosting với safety
        try:
            keyword_config = self._apply_keyword_boosts(query, search_config)
            if keyword_config and isinstance(keyword_config, dict):
                search_config = self._merge_configs(search_config, keyword_config)
                self.stats['keyword_boosts'] += 1
        except Exception as e:
            logger.warning(f"Keyword boosting failed: {e}")
        
        # STEP 5: Context enhancement với null safety
        try:
            if unified_context and isinstance(unified_context, dict) and unified_context.get('has_context'):
                context_config = self._enhance_with_context(search_config, unified_context)
                if context_config and isinstance(context_config, dict):
                    search_config = self._merge_configs(search_config, context_config)
        except Exception as e:
            logger.warning(f"Context enhancement failed: {e}")
        
        # FINAL: Always ensure valid structure
        search_config['debug_info'] = {
            'mappings_applied': [search_config['method']],
            'total_boosts': len(search_config.get('boost_keywords', [])),
            'target_articles_count': len(search_config.get('target_articles', [])),
            'mapping_success': mapping_applied
        }
        
        logger.debug(f"Mapping result: {search_config['method']} -> {len(search_config['target_articles'])} articles")
        
        # CRITICAL: Never return None, always return valid dict
        return search_config
    
    def _build_intent_mappings(self) -> Dict[str, Dict]:
        """HARDCODE: Intent từ unified_processor → search config"""
        return {
            # HỘ CHIẾU - PROCEDURES
            'procedure': {
                'passport_procedure': {
                    'target_articles': ['15', '16', '14'],
                    'boost_keywords': ['thủ tục', 'hồ sơ', 'cấp hộ chiếu', 'tờ khai', 'ảnh chân dung'],
                    'filter_content_types': ['legal_document', 'qa_entry'],
                    'search_strategy': 'procedure_focused',
                    'confidence_multiplier': 1.3,
                    'k_multiplier': 1.5
                }
            },
            
            # HỘ CHIẾU - COST
            'cost': {
                'passport_cost': {
                    'target_articles': ['15', '16'],  # Lệ phí thường ở procedure articles
                    'boost_keywords': ['lệ phí', 'phí', 'chi phí', 'tiền', 'dịch vụ chuyển phát'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'cost_specific',
                    'confidence_multiplier': 1.4,
                    'threshold_adjustment': -0.1  # Lower threshold for cost queries
                }
            },
            
            # HỘ CHIẾU - TIME  
            'time': {
                'passport_time': {
                    'target_articles': ['15', '16', '7'],
                    'boost_keywords': ['thời hạn', 'ngày làm việc', 'bao lâu', 'khi nào', 'thời gian'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'time_specific',
                    'confidence_multiplier': 1.2
                }
            },
            
            # ELIGIBILITY (có được không)
            'eligibility': {
                'passport_eligibility': {
                    'target_articles': ['14', '21', '33', '34'],
                    'boost_keywords': ['đối tượng', 'điều kiện', 'được cấp', 'có được', 'được phép'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'eligibility_focused',
                    'confidence_multiplier': 1.3
                }
            },
            
            # XUẤT CẢNH - NHẬP CẢNH
            'exit_entry': {
                'exit_conditions': {
                    'target_articles': ['33', '34', '35'],
                    'boost_keywords': ['xuất cảnh', 'nhập cảnh', 'điều kiện', 'thị thực', 'visa'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'exit_entry_focused',
                    'confidence_multiplier': 1.4
                }
            },
            
            # TẠM HOÃN XUẤT CẢNH
            'suspension': {
                'exit_suspension': {
                    'target_articles': ['36', '37', '38', '39'],
                    'boost_keywords': ['tạm hoãn', 'cấm xuất cảnh', 'không được', 'bị cấm'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'suspension_focused',
                    'confidence_multiplier': 1.5
                }
            },
            
            # LEGAL REFERENCE (Điều X)
            'legal_reference': {
                'specific_article': {
                    'target_articles': [],  # Will be determined by article detection
                    'boost_keywords': ['điều', 'khoản', 'điểm', 'quy định'],
                    'filter_content_types': ['legal_document'],
                    'search_strategy': 'legal_precise',
                    'confidence_multiplier': 2.0,  # High confidence for specific articles
                    'threshold_adjustment': -0.2
                }
            }
        }
    
    def _build_query_shortcuts(self) -> Dict[str, Dict]:
        """HARDCODE: TOÀN BỘ query patterns → instant targeting"""
        return {
            # ĐIỀU 1-5: QUY ĐỊNH CHUNG
            'phạm vi điều chỉnh': {
                'target_articles': ['1'],
                'boost_keywords': ['phạm vi', 'điều chỉnh', 'luật'],
                'confidence_multiplier': 1.4
            },
            'định nghĩa xuất cảnh': {
                'target_articles': ['2'],
                'boost_keywords': ['định nghĩa', 'xuất cảnh', 'giải thích'],
                'confidence_multiplier': 1.5
            },
            'định nghĩa nhập cảnh': {
                'target_articles': ['2'],
                'boost_keywords': ['định nghĩa', 'nhập cảnh', 'giải thích'],
                'confidence_multiplier': 1.5
            },
            'định nghĩa hộ chiếu': {
                'target_articles': ['2'],
                'boost_keywords': ['định nghĩa', 'hộ chiếu', 'giải thích'],
                'confidence_multiplier': 1.5
            },
            'nguyên tắc xuất cảnh nhập cảnh': {
                'target_articles': ['3'],
                'boost_keywords': ['nguyên tắc', 'tuân thủ'],
                'confidence_multiplier': 1.4
            },
            'hành vi bị nghiêm cấm': {
                'target_articles': ['4'],
                'boost_keywords': ['nghiêm cấm', 'vi phạm', 'hành vi'],
                'confidence_multiplier': 1.6
            },
            'quyền nghĩa vụ công dân': {
                'target_articles': ['5'],
                'boost_keywords': ['quyền', 'nghĩa vụ', 'công dân'],
                'confidence_multiplier': 1.5
            },

            # ĐIỀU 6-7: GIẤY TỜ
            'loại giấy tờ xuất nhập cảnh': {
                'target_articles': ['6'],
                'boost_keywords': ['loại giấy tờ', 'hộ chiếu ngoại giao', 'hộ chiếu công vụ'],
                'confidence_multiplier': 1.5
            },
            'hộ chiếu có chíp': {
                'target_articles': ['6'],
                'boost_keywords': ['chíp điện tử', 'gắn chíp'],
                'confidence_multiplier': 1.4
            },
            'thời hạn hộ chiếu': {
                'target_articles': ['7'],
                'boost_keywords': ['thời hạn', 'gia hạn', '10 năm', '5 năm'],
                'confidence_multiplier': 1.5
            },

            # ĐIỀU 8-13: HỘ CHIẾU NGOẠI GIAO, CÔNG VỤ
            'hộ chiếu ngoại giao': {
                'target_articles': ['8', '12'],
                'boost_keywords': ['ngoại giao', 'đối tượng được cấp'],
                'confidence_multiplier': 1.4
            },
            'hộ chiếu công vụ': {
                'target_articles': ['9', '12'],
                'boost_keywords': ['công vụ', 'cán bộ', 'công chức'],
                'confidence_multiplier': 1.4
            },
            'thủ tục hộ chiếu công vụ': {
                'target_articles': ['12', '13'],
                'boost_keywords': ['thủ tục', 'cấp', 'gia hạn'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 14-16: HỘ CHIẾU PHỔ THÔNG - Top queries
            'ai được làm hộ chiếu': {
                'target_articles': ['14'],
                'boost_keywords': ['đối tượng được cấp', 'công dân việt nam'],
                'confidence_multiplier': 1.5
            },
            'thủ tục làm hộ chiếu': {
                'target_articles': ['15'],
                'boost_keywords': ['thủ tục', 'hồ sơ', 'tờ khai'],
                'confidence_multiplier': 1.6
            },
            'làm hộ chiếu cần gì': {
                'target_articles': ['15'],
                'boost_keywords': ['giấy tờ liên quan', 'hồ sơ', 'cần'],
                'confidence_multiplier': 1.6
            },
            'hồ sơ hộ chiếu': {
                'target_articles': ['15'],
                'boost_keywords': ['hồ sơ đề nghị', 'giấy tờ'],
                'confidence_multiplier': 1.5
            },
            'hồ sơ làm hộ chiếu': {
                'target_articles': ['15'],
                'boost_keywords': ['hồ sơ đề nghị', 'tờ khai', 'ảnh'],
                'confidence_multiplier': 1.5
            },
            'bao lâu có hộ chiếu': {
                'target_articles': ['15'],
                'boost_keywords': ['thời hạn', 'ngày làm việc'],
                'confidence_multiplier': 1.4
            },
            'thời gian làm hộ chiếu': {
                'target_articles': ['15', '16'],
                'boost_keywords': ['thời hạn giải quyết', 'ngày làm việc'],
                'confidence_multiplier': 1.4
            },
            'lệ phí hộ chiếu': {
                'target_articles': ['15'],
                'boost_keywords': ['lệ phí', 'phí dịch vụ'],
                'confidence_multiplier': 1.5
            },
            'làm hộ chiếu ở nước ngoài': {
                'target_articles': ['16'],
                'boost_keywords': ['nước ngoài', 'cơ quan đại diện'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 17-18: THỦ TỤC RÚT GỌN
            'hộ chiếu rút gọn': {
                'target_articles': ['17', '18'],
                'boost_keywords': ['rút gọn', 'mất hộ chiếu'],
                'confidence_multiplier': 1.4
            },
            'mất hộ chiếu ở nước ngoài': {
                'target_articles': ['18'],
                'boost_keywords': ['mất hộ chiếu', 'về nước ngay'],
                'confidence_multiplier': 1.5
            },

            # ĐIỀU 19-20: GIẤY THÔNG HÀNH
            'giấy thông hành': {
                'target_articles': ['19', '20'],
                'boost_keywords': ['thông hành', 'biên giới', 'láng giềng'],
                'confidence_multiplier': 1.4
            },
            'qua lại biên giới': {
                'target_articles': ['19'],
                'boost_keywords': ['biên giới', 'láng giềng', 'cư trú'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 21-22: CHƯA CẤP
            'không được cấp hộ chiếu': {
                'target_articles': ['21'],
                'boost_keywords': ['chưa cấp', 'vi phạm hành chính', 'tạm hoãn'],
                'confidence_multiplier': 1.5
            },
            'trường hợp chưa cấp': {
                'target_articles': ['21'],
                'boost_keywords': ['chưa cấp', 'trường hợp', 'vi phạm'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 23-32: QUẢN LÝ, THU HỒI
            'trách nhiệm người được cấp': {
                'target_articles': ['23'],
                'boost_keywords': ['trách nhiệm', 'giữ gìn', 'bảo quản'],
                'confidence_multiplier': 1.3
            },
            'quản lý hộ chiếu': {
                'target_articles': ['24'],
                'boost_keywords': ['quản lý', 'giao nhận'],
                'confidence_multiplier': 1.3
            },
            'sử dụng hộ chiếu': {
                'target_articles': ['25', '26'],
                'boost_keywords': ['sử dụng', 'công tác nước ngoài'],
                'confidence_multiplier': 1.3
            },
            'thu hồi hộ chiếu': {
                'target_articles': ['27', '29', '30', '31'],
                'boost_keywords': ['thu hồi', 'hủy giá trị'],
                'confidence_multiplier': 1.4
            },
            'mất hộ chiếu': {
                'target_articles': ['28'],
                'boost_keywords': ['mất', 'báo mất', '48 giờ'],
                'confidence_multiplier': 1.5
            },
            'báo mất hộ chiếu': {
                'target_articles': ['28'],
                'boost_keywords': ['báo mất', '48 giờ', 'đơn báo'],
                'confidence_multiplier': 1.5
            },
            'khôi phục hộ chiếu': {
                'target_articles': ['32'],
                'boost_keywords': ['khôi phục', 'tìm lại', 'thị thực'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 33-39: XUẤT CẢNH, NHẬP CẢNH - Top queries
            'điều kiện xuất cảnh': {
                'target_articles': ['33'],
                'boost_keywords': ['điều kiện xuất cảnh', 'giấy tờ', '6 tháng'],
                'confidence_multiplier': 1.6
            },
            'điều kiện nhập cảnh': {
                'target_articles': ['34'],
                'boost_keywords': ['điều kiện nhập cảnh', 'giấy tờ'],
                'confidence_multiplier': 1.6
            },
            'được xuất cảnh không': {
                'target_articles': ['33'],
                'boost_keywords': ['được xuất cảnh', 'điều kiện'],
                'confidence_multiplier': 1.5
            },
            'cần visa không': {
                'target_articles': ['33'],
                'boost_keywords': ['thị thực', 'visa', 'miễn thị thực'],
                'confidence_multiplier': 1.4
            },
            'kiểm soát xuất nhập cảnh': {
                'target_articles': ['35'],
                'boost_keywords': ['kiểm soát', 'cửa khẩu', 'xuất trình'],
                'confidence_multiplier': 1.4
            },
            'tạm hoãn xuất cảnh': {
                'target_articles': ['36', '37'],
                'boost_keywords': ['tạm hoãn xuất cảnh', 'trường hợp'],
                'confidence_multiplier': 1.7
            },
            'bị cấm xuất cảnh': {
                'target_articles': ['36'],
                'boost_keywords': ['tạm hoãn', 'bị cấm', 'không được'],
                'confidence_multiplier': 1.6
            },
            'bị can bị cáo': {
                'target_articles': ['36'],
                'boost_keywords': ['bị can', 'bị cáo', 'tạm hoãn'],
                'confidence_multiplier': 1.5
            },
            'nợ thuế': {
                'target_articles': ['36'],
                'boost_keywords': ['nghĩa vụ thuế', 'nộp thuế', 'cưỡng chế'],
                'confidence_multiplier': 1.4
            },
            'dịch bệnh': {
                'target_articles': ['36'],
                'boost_keywords': ['dịch bệnh', 'nguy hiểm', 'lây lan'],
                'confidence_multiplier': 1.4
            },
            'thẩm quyền tạm hoãn': {
                'target_articles': ['37'],
                'boost_keywords': ['thẩm quyền', 'quyết định'],
                'confidence_multiplier': 1.4
            },
            'thời hạn tạm hoãn': {
                'target_articles': ['38'],
                'boost_keywords': ['thời hạn', 'gia hạn', '1 năm'],
                'confidence_multiplier': 1.4
            },

            # ĐIỀU 40-43: CƠ SỞ DỮ LIỆU
            'cơ sở dữ liệu quốc gia': {
                'target_articles': ['40', '41'],
                'boost_keywords': ['cơ sở dữ liệu', 'quốc gia'],
                'confidence_multiplier': 1.3
            },
            'thông tin cơ sở dữ liệu': {
                'target_articles': ['41'],
                'boost_keywords': ['thông tin', 'vân tay', 'ảnh chân dung'],
                'confidence_multiplier': 1.3
            },
            'thu thập thông tin': {
                'target_articles': ['42'],
                'boost_keywords': ['thu thập', 'cập nhật'],
                'confidence_multiplier': 1.2
            },
            'khai thác dữ liệu': {
                'target_articles': ['43'],
                'boost_keywords': ['khai thác', 'quản lý'],
                'confidence_multiplier': 1.2
            },

            # ĐIỀU 44-50: TRÁCH NHIỆM CÁC CƠ QUAN
            'trách nhiệm quản lý': {
                'target_articles': ['44'],
                'boost_keywords': ['trách nhiệm', 'quản lý nhà nước'],
                'confidence_multiplier': 1.2
            },
            'bộ công an': {
                'target_articles': ['45'],
                'boost_keywords': ['bộ công an', 'trách nhiệm'],
                'confidence_multiplier': 1.3
            },
            'bộ ngoại giao': {
                'target_articles': ['46'],
                'boost_keywords': ['bộ ngoại giao', 'cơ quan lãnh sự'],
                'confidence_multiplier': 1.3
            },
            'bộ quốc phòng': {
                'target_articles': ['47'],
                'boost_keywords': ['bộ quốc phòng', 'cửa khẩu'],
                'confidence_multiplier': 1.2
            },
            'cơ quan đại diện': {
                'target_articles': ['48'],
                'boost_keywords': ['đại diện việt nam', 'nước ngoài'],
                'confidence_multiplier': 1.2
            },

            # ĐIỀU 51-52: THI HÀNH
            'hiệu lực': {
                'target_articles': ['51'],
                'boost_keywords': ['hiệu lực', 'thi hành'],
                'confidence_multiplier': 1.1
            },
            'chuyển tiếp': {
                'target_articles': ['52'],
                'boost_keywords': ['chuyển tiếp', 'giấy tờ cũ'],
                'confidence_multiplier': 1.1
            }
        }
    
    def _build_article_targets(self) -> Dict[str, Dict]:
        """HARDCODE: Specific articles → exact targeting"""
        return {
            # Core passport articles
            '1': {
                'boost_multiplier': 3.0,
                'related_articles': [],
                'topics': ['phạm vi điều chỉnh'],
                'search_strategy': 'legal_precise',
                'short_content_boost': 2.0
            },
            '14': {
                'boost_multiplier': 3.0,
                'related_articles': ['15'],
                'topics': ['đối tượng được cấp'],
                'search_strategy': 'legal_precise',
                'short_content_boost': 2.0
            },
            '15': {
                'boost_multiplier': 2.0,
                'related_articles': ['14', '16'],
                'topics': ['thủ tục_hộ_chiếu', 'hồ_sơ', 'trong_nước'],
                'search_strategy': 'legal_precise'
            },
            
            '16': {
                'boost_multiplier': 2.0, 
                'related_articles': ['15'],
                'topics': ['hộ_chiếu_nước_ngoài'],
                'search_strategy': 'legal_precise'
            },
            
            '14': {
                'boost_multiplier': 1.8,
                'related_articles': ['15'],
                'topics': ['đối_tượng_được_cấp'],
                'search_strategy': 'legal_precise'
            },
            
            '7': {
                'boost_multiplier': 1.5,
                'related_articles': ['6'],
                'topics': ['thời_hạn_giấy_tờ'],
                'search_strategy': 'legal_precise'
            },
            
            # Exit/Entry articles
            '33': {
                'boost_multiplier': 2.0,
                'related_articles': ['34', '35'],
                'topics': ['kiện_xuất_cảnh'],
                'search_strategy': 'legal_precise'
            },
            
            '34': {
                'boost_multiplier': 2.0,
                'related_articles': ['33', '35'],
                'topics': ['kiện_nhập_cảnh'],
                'search_strategy': 'legal_precise'
            },
            
            # Suspension articles
            '36': {
                'boost_multiplier': 2.2,
                'related_articles': ['37', '38'],
                'topics': ['tạm_hoãn_xuất_cảnh', 'trường_hợp_bị_cấm'],
                'search_strategy': 'legal_precise'
            },
            
            '37': {
                'boost_multiplier': 1.8,
                'related_articles': ['36'],
                'topics': ['thẩm_quyền_tạm_hoãn'],
                'search_strategy': 'legal_precise'
            }
        }
    
    def _build_keyword_boosts(self) -> Dict[str, float]:
        """HARDCODE: TOÀN BỘ keyword boost values cho 52 điều"""
        return {
            # ĐIỀU 1-5: QUY ĐỊNH CHUNG - High priority
            'phạm vi điều chỉnh': 1.5,
            'xuất cảnh': 1.6,
            'nhập cảnh': 1.6,
            'hộ chiếu': 1.4,
            'giấy thông hành': 1.3,
            'kiểm soát xuất nhập cảnh': 1.4,
            'cơ sở dữ liệu': 1.2,
            'định nghĩa': 1.4,
            'giải thích từ ngữ': 1.3,
            'nguyên tắc': 1.3,
            'hành vi nghiêm cấm': 1.5,
            'quyền nghĩa vụ': 1.4,

            # ĐIỀU 6-7: GIẤY TỜ - High priority
            'giấy tờ xuất nhập cảnh': 1.5,
            'hộ chiếu ngoại giao': 1.4,
            'hộ chiếu công vụ': 1.4,
            'hộ chiếu phổ thông': 1.6,
            'chíp điện tử': 1.3,
            'thời hạn': 1.5,
            'gia hạn': 1.4,
            '10 năm': 1.3,
            '5 năm': 1.3,

            # ĐIỀU 8-13: HỘ CHIẾU NGOẠI GIAO, CÔNG VỤ
            'ngoại giao': 1.3,
            'công vụ': 1.3,
            'cán bộ': 1.2,
            'công chức': 1.2,
            'viên chức': 1.2,
            'sĩ quan': 1.2,
            'thẩm quyền': 1.3,
            'cử đi công tác': 1.3,

            # ĐIỀU 14-16: HỘ CHIẾU PHỔ THÔNG - Highest priority
            'thủ tục': 1.7,
            'hồ sơ': 1.6,
            'cấp hộ chiếu': 1.7,
            'làm hộ chiếu': 1.6,
            'tờ khai': 1.4,
            'ảnh chân dung': 1.3,
            'vân tay': 1.2,
            'giấy tờ liên quan': 1.5,
            'chứng minh nhân dân': 1.3,
            'căn cước công dân': 1.3,
            'giấy khai sinh': 1.3,
            'thời hạn giải quyết': 1.5,
            '05 ngày làm việc': 1.4,
            '08 ngày làm việc': 1.4,
            '03 ngày làm việc': 1.4,
            'lệ phí': 1.6,
            'phí dịch vụ': 1.3,
            'chuyển phát': 1.2,
            'trong nước': 1.3,
            'nước ngoài': 1.3,
            'cơ quan đại diện': 1.3,

            # ĐIỀU 17-18: THỦ TỤC RÚT GỌN
            'rút gọn': 1.4,
            'mất hộ chiếu': 1.5,
            'về nước ngay': 1.4,
            'trục xuất': 1.3,
            'nhận trở lại': 1.3,

            # ĐIỀU 19-20: GIẤY THÔNG HÀNH
            'giấy thông hành': 1.4,
            'biên giới': 1.4,
            'láng giềng': 1.3,
            'qua lại': 1.3,
            'cư trú': 1.2,
            '12 tháng': 1.2,

            # ĐIỀU 21-22: CHƯA CẤP
            'chưa cấp': 1.5,
            'không được cấp': 1.5,
            'vi phạm hành chính': 1.4,

            # ĐIỀU 23-32: QUẢN LÝ, THU HỒI
            'trách nhiệm': 1.3,
            'giữ gìn': 1.2,
            'bảo quản': 1.2,
            'quản lý': 1.3,
            'sử dụng': 1.3,
            'thu hồi': 1.5,
            'hủy giá trị': 1.4,
            'báo mất': 1.5,
            '48 giờ': 1.4,
            'đơn báo mất': 1.4,
            'khôi phục': 1.4,
            'tìm lại': 1.3,
            'thôi quốc tịch': 1.3,
            'tước quốc tịch': 1.3,

            # ĐIỀU 33-39: XUẤT CẢNH, NHẬP CẢNH - Highest priority
            'điều kiện': 1.7,
            'điều kiện xuất cảnh': 1.8,
            'điều kiện nhập cảnh': 1.7,
            'được cấp': 1.5,
            'có được': 1.5,
            'được phép': 1.5,
            'thị thực': 1.6,
            'visa': 1.5,
            'miễn thị thực': 1.4,
            '6 tháng': 1.4,
            'còn hạn': 1.3,
            'kiểm soát': 1.4,
            'cửa khẩu': 1.3,
            'xuất trình': 1.3,
            'biên bản': 1.2,

            # TẠM HOÃN - Highest priority  
            'tạm hoãn': 1.8,
            'tạm hoãn xuất cảnh': 1.9,
            'bị cấm': 1.6,
            'không được': 1.5,
            'bị can': 1.4,
            'bị cáo': 1.4,
            'chấp hành án': 1.4,
            'nghĩa vụ thuế': 1.5,
            'nợ thuế': 1.5,
            'cưỡng chế': 1.4,
            'thanh tra': 1.3,
            'kiểm tra': 1.3,
            'dịch bệnh': 1.4,
            'nguy hiểm': 1.3,
            'lây lan': 1.3,
            'quốc phòng': 1.3,
            'an ninh': 1.3,
            'quyết định': 1.4,
            '1 năm': 1.2,
            '6 tháng': 1.2,

            # ĐIỀU 40-43: CƠ SỞ DỮ LIỆU
            'cơ sở dữ liệu': 1.3,
            'quốc gia': 1.2,
            'thông tin': 1.2,
            'thu thập': 1.2,
            'cập nhật': 1.2,
            'khai thác': 1.2,
            'bảo mật': 1.2,
            'an toàn': 1.2,

            # ĐIỀU 44-50: TRÁCH NHIỆM CÁC CƠ QUAN
            'bộ công an': 1.3,
            'bộ ngoại giao': 1.3,
            'bộ quốc phòng': 1.2,
            'cơ quan lãnh sự': 1.3,
            'ban cơ yếu': 1.2,
            'chính phủ': 1.2,

            # GENERAL LEGAL TERMS
            'điều': 1.4,
            'khoản': 1.3,
            'điểm': 1.3,
            'quy định': 1.3,
            'luật': 1.2,
            'nghị định': 1.2,
            'công dân việt nam': 1.3,
            'pháp luật': 1.2,
            'văn bản': 1.2,
            'mẫu': 1.2,
            'trường hợp': 1.3,
            'căn cứ': 1.2,
            'theo quy định': 1.2
        }
    
    def _build_search_strategies(self) -> Dict[str, Dict]:
        """HARDCODE: Search strategies per intent type"""
        return {
            'procedure_focused': {
                'qa_priority': True,
                'qa_boost': 1.3,
                'threshold': 0.2,
                'max_results': 15
            },
            
            'legal_precise': {
                'qa_priority': False,
                'legal_boost': 1.5,
                'threshold': 0.15,
                'exact_matching': True,
                'max_results': 10
            },
            
            'cost_specific': {
                'qa_priority': True,
                'keyword_heavy': True,
                'threshold': 0.25,
                'max_results': 8
            },
            
            'time_specific': {
                'qa_priority': True,
                'threshold': 0.22,
                'max_results': 10
            },
            
            'eligibility_focused': {
                'qa_priority': False,
                'legal_boost': 1.3,
                'threshold': 0.18,
                'max_results': 12
            },
            
            'exit_entry_focused': {
                'qa_priority': False,
                'legal_boost': 1.4,
                'threshold': 0.16,
                'max_results': 12
            },
            
            'suspension_focused': {
                'qa_priority': False,
                'legal_boost': 1.6,
                'threshold': 0.14,
                'max_results': 10
            },
            
            'balanced': {
                'qa_priority': None,
                'threshold': 0.2,
                'max_results': 12
            }
        }
    
    def _map_by_articles(self, query: str) -> Optional[Dict]:
        query_lower = query.lower()
        article_patterns = [r'điều\s+(\d+)', r'article\s+(\d+)']
        for pattern in article_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                article = matches[0]
                return {
                    'target_articles': [article],
                    'search_strategy': 'exact_match',  # Ép dùng exact_match
                    'confidence_multiplier': 6.0,  # Tăng boost
                    'k_multiplier': 5.0,  # Tăng số lượng kết quả
                    'filter_content_types': ['legal_document'],
                    'boost_keywords': ['điều', f'điều {article}', 'phạm vi' if article == '1' else 'đối tượng' if article == '14' else 'yêu cầu xây dựng'],
                    'law_unit_filter': f"^{article}($|\\.)",  # Match "1", "1.x"
                    'short_content_boost': 3.0  # Tăng boost chunk ngắn
                }
        return None

    def _map_by_intent(self, intent_analysis: dict) -> Optional[Dict]:
        """FIXED: Better null handling and validation"""
        if not intent_analysis or not isinstance(intent_analysis, dict):
            return None
        
        try:
            intent_type = intent_analysis.get('intent_type', '')
            if not intent_type:
                return None
            
            # Rest of mapping logic...
            for category, intents in self.intent_mappings.items():
                if intent_type in category or category in intent_type:
                    for intent_name, config in intents.items():
                        if isinstance(config, dict):  # Validate config structure
                            return config.copy()
            
            # Fallback mappings với validation
            intent_fallbacks = {
                'procedure': self.intent_mappings.get('procedure', {}).get('passport_procedure'),
                'cost': self.intent_mappings.get('cost', {}).get('passport_cost'),
                'time': self.intent_mappings.get('time', {}).get('passport_time'),
                'eligibility': self.intent_mappings.get('eligibility', {}).get('passport_eligibility'),
                'legal_reference': self.intent_mappings.get('legal_reference', {}).get('specific_article')
            }
            
            fallback = intent_fallbacks.get(intent_type)
            return fallback.copy() if fallback and isinstance(fallback, dict) else None
            
        except Exception as e:
            logger.warning(f"Intent mapping error: {e}")
            return None
    
    def _map_by_query_patterns(self, query: str) -> Optional[Dict]:
        """Map by direct query patterns"""
        query_lower = query.lower().strip()
        
        # Exact pattern matching
        for pattern, config in self.query_shortcuts.items():
            if pattern in query_lower:
                return config.copy()
        
        # Fuzzy pattern matching
        for pattern, config in self.query_shortcuts.items():
            pattern_words = set(pattern.split())
            query_words = set(query_lower.split())
            
            overlap = len(pattern_words & query_words)
            if overlap >= len(pattern_words) * 0.7:  # 70% overlap
                return config.copy()
        
        return None
    
    
    def _map_by_articles(self, query: str) -> Optional[Dict]:
        """FIXED: Better pattern matching và validation"""
        if not query or not isinstance(query, str):
            return None
            
        try:
            query_lower = query.lower()
            article_patterns = [r'điều\s+(\d+)', r'article\s+(\d+)']
            
            for pattern in article_patterns:
                try:
                    matches = re.findall(pattern, query_lower)
                    if matches and matches[0]:  # Ensure match exists và not empty
                        article = matches[0]
                        # Validate article number
                        if article.isdigit() and 1 <= int(article) <= 52:  # Valid range for law
                            return {
                                'target_articles': [article],
                                'expected_law_unit': article,
                                'search_strategy': 'exact_match',
                                'confidence_multiplier': 10.0,
                                'k_multiplier': 20.0,
                                'filter_content_types': ['legal_document'],
                                'boost_keywords': ['điều', f'điều {article}'],
                                'law_unit_filter': f"^{article}($|\\.)",
                                'short_content_boost': 5.0
                            }
                except re.error as e:
                    logger.warning(f"Regex error in article pattern {pattern}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Article mapping error: {e}")
            return None   

    
    def _apply_keyword_boosts(self, query: str, current_config: Dict) -> Optional[Dict]:
        """Apply keyword-based boosts"""
        query_lower = query.lower()
        boost_keywords = []
        total_boost = 1.0
        
        for keyword, boost_value in self.keyword_boost_rules.items():
            if keyword in query_lower:
                boost_keywords.append(keyword)
                total_boost *= boost_value
        
        if boost_keywords:
            return {
                'boost_keywords': boost_keywords,
                'confidence_multiplier': total_boost,
                'keyword_boost_applied': True
            }
        
        return None
    
    def _enhance_with_context(self, current_config: Dict, unified_context: dict) -> Dict:
        """Enhance config với conversation context"""
        enhancements = {}
        
        # Topic thread boost
        topic_thread = unified_context.get('topic_thread')
        if topic_thread:
            topic_boosts = {
                'hộ chiếu': 1.2,
                'xuất cảnh': 1.3,
                'nhập cảnh': 1.3,
                'visa': 1.2
            }
            
            if topic_thread in topic_boosts:
                enhancements['confidence_multiplier'] = current_config.get('confidence_multiplier', 1.0) * topic_boosts[topic_thread]
        
        # Citizen profile boost
        citizen_profile = unified_context.get('citizen_profile', {})
        if citizen_profile.get('age_group') == 'minor':
            enhancements['boost_keywords'] = current_config.get('boost_keywords', []) + ['trẻ em', 'chưa đủ 14 tuổi']
        
        return enhancements
    
    def _merge_configs(self, base_config: Dict, additional_config: Dict) -> Dict:
        """Merge multiple configs intelligently"""
        merged = base_config.copy()
        
        for key, value in additional_config.items():
            if key in ['target_articles', 'boost_keywords', 'filter_content_types']:
                # Merge lists
                merged[key] = list(set(merged.get(key, []) + value))
            elif key == 'confidence_multiplier':
                # Multiply confidence
                merged[key] = merged.get(key, 1.0) * value
            else:
                # Override other values
                merged[key] = value
        
        return merged
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mapping statistics"""
        return {
            'version': 'XuatNhapCanhMapping v1.0',
            'law_basis': 'Luật 49/2019/QH14',
            'performance': self.stats,
            'capabilities': {
                'intent_mappings': len(self.intent_mappings),
                'query_shortcuts': len(self.query_shortcuts),
                'article_targets': len(self.article_targets),
                'keyword_boosts': len(self.keyword_boost_rules),
                'search_strategies': len(self.search_strategies)
            },
            'coverage': {
                'main_procedures': ['15', '16', '14'],
                'exit_entry': ['33', '34', '35'],
                'suspension': ['36', '37', '38'],
                'core_intents': ['procedure', 'cost', 'time', 'eligibility', 'legal_reference']
            }
        }

# Factory function
def create_xuatnhapcanh_mapping() -> XuatNhapCanhMapping:
    """Create mapping instance for xuất nhập cảnh domain"""
    return XuatNhapCanhMapping()