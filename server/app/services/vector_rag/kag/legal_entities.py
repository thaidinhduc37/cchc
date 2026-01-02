# app/services/vector_rag/kag/legal_entities.py

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

@dataclass
class LegalEntity:
    """Represents a legal entity found in text"""
    text: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    canonical_form: str = None

class LegalEntityExtractor:
    """
    Extracts legal entities from Vietnamese legal queries
    Focuses on immigration law domain with expandable patterns
    """
    
    def __init__(self):
        self.entity_patterns = self._init_entity_patterns()
        self.legal_dictionary = self._init_legal_dictionary()
        self.abbreviations = self._init_abbreviations()
    
    def _init_entity_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for different entity types"""
        return {
            'law_document': [
                r'Luật\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'Nghị\s+định\s+số\s+(\d+/\d+/NĐ-CP)',
                r'Thông\s+tư\s+số\s+(\d+/\d+/TT-[A-Z]+)',
                r'Quyết\s+định\s+số\s+(\d+/\d+/QĐ-[A-Z]+)',
                r'Bộ\s+luật\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'Điều\s+(\d+)',
                r'Khoản\s+(\d+)',
                r'Điểm\s+([a-z])',
            ],
            'procedure': [
                r'thủ\s+tục\s+([a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'quy\s+trình\s+([a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'giấy\s+tờ\s+([a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'hồ\s+sơ\s+([a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
            ],
            'visa_type': [
                r'visa\s+(DT|DN|LD|LĐ|TT|DL|C1|C2|C3|B1|B2|B3|B4)',
                r'thị\s+thực\s+(nhập\s+cảnh|xuất\s+cảnh|quá\s+cảnh)',
                r'giấy\s+phép\s+(lao\s+động|tạm\s+trú|thường\s+trú)',
                r'thẻ\s+(tạm\s+trú|thường\s+trú|lao\s+động)',
            ],
            'agency': [
                r'Bộ\s+Công\s+an',
                r'Bộ\s+Ngoại\s+giao',
                r'Cục\s+Quản\s+lý\s+xuất\s+nhập\s+cảnh',
                r'Phòng\s+Quản\s+lý\s+xuất\s+nhập\s+cảnh',
                r'Sở\s+Ngoại\s+vụ',
                r'UBND\s+(tỉnh|thành\s+phố|huyện|xã)',
                r'Đại\s+sứ\s+quán',
                r'Lãnh\s+sự\s+quán',
            ],
            'duration': [
                r'(\d+)\s+(ngày|tháng|năm)',
                r'trong\s+vòng\s+(\d+)\s+(ngày|tháng|năm)',
                r'tối\s+đa\s+(\d+)\s+(ngày|tháng|năm)',
                r'không\s+quá\s+(\d+)\s+(ngày|tháng|năm)',
            ],
            'fee': [
                r'(\d+(?:\.\d+)?)\s+(VND|USD|đồng)',
                r'lệ\s+phí\s+(\d+(?:\.\d+)?)\s+(VND|USD|đồng)',
                r'phí\s+(\d+(?:\.\d+)?)\s+(VND|USD|đồng)',
            ],
            'location': [
                r'tại\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
                r'ở\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+)',
            ]
        }
    
    def _init_legal_dictionary(self) -> Dict[str, List[str]]:
        """Initialize legal term dictionary with synonyms"""
        return {
            'visa_types': [
                'visa', 'thị thực', 'giấy phép nhập cảnh', 'giấy phép xuất cảnh',
                'visa du lịch', 'visa công tác', 'visa lao động', 'visa thăm thân',
                'visa quá cảnh', 'visa ngoại giao', 'visa công vụ'
            ],
            'documents': [
                'hộ chiếu', 'passport', 'chứng minh nhân dân', 'căn cước công dân',
                'giấy khai sinh', 'giấy chứng nhận kết hôn', 'bằng cấp', 'bằng tốt nghiệp',
                'giấy khám sức khỏe', 'giấy chứng nhận lý lịch tư pháp', 'CV', 'sơ yếu lý lịch',
                'hợp đồng lao động', 'thư mời', 'giấy bảo lãnh', 'giấy xác nhận tài chính'
            ],
            'procedures': [
                'thủ tục nhập cảnh', 'thủ tục xuất cảnh', 'thủ tục xin visa',
                'thủ tục gia hạn visa', 'thủ tục đổi loại visa', 'thủ tục xin thường trú',
                'thủ tục xin tạm trú', 'thủ tục xin giấy phép lao động',
                'thủ tục kết hôn với người nước ngoài', 'thủ tục nhập quốc tịch'
            ],
            'agencies': [
                'Bộ Công an', 'Bộ Ngoại giao', 'Cục Quản lý xuất nhập cảnh',
                'Phòng Quản lý xuất nhập cảnh', 'Sở Ngoại vụ', 'UBND',
                'Đại sứ quán', 'Lãnh sự quán', 'Cơ quan đại diện'
            ],
            'statuses': [
                'người nước ngoài', 'công dân Việt Nam', 'người không quốc tịch',
                'người Việt Nam định cư ở nước ngoài', 'chuyên gia', 'nhà đầu tư',
                'lao động', 'học sinh', 'sinh viên', 'du khách', 'thăm thân'
            ]
        }
    
    def _init_abbreviations(self) -> Dict[str, str]:
        """Initialize common abbreviations and their full forms"""
        return {
            'NĐ-CP': 'Nghị định của Chính phủ',
            'TT-BCA': 'Thông tư của Bộ Công an',
            'QĐ-TTg': 'Quyết định của Thủ tướng Chính phủ',
            'UBND': 'Ủy ban nhân dân',
            'QLXNC': 'Quản lý xuất nhập cảnh',
            'CMND': 'Chứng minh nhân dân',
            'CCCD': 'Căn cước công dân',
            'GPLĐ': 'Giấy phép lao động',
            'TTXNC': 'Thị thực xuất nhập cảnh',
            'ĐSQVN': 'Đại sứ quán Việt Nam',
            'LSQVN': 'Lãnh sự quán Việt Nam'
        }
    
    def extract_entities(self, text: str) -> List[LegalEntity]:
        """
        Extract legal entities from text
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of LegalEntity objects
        """
        entities = []
        text_lower = text.lower()
        
        # Extract using regex patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity = LegalEntity(
                        text=match.group(0),
                        entity_type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9,
                        canonical_form=self._get_canonical_form(match.group(0))
                    )
                    entities.append(entity)
        
        # Extract using dictionary lookup
        for category, terms in self.legal_dictionary.items():
            for term in terms:
                if term.lower() in text_lower:
                    start_pos = text_lower.find(term.lower())
                    entity = LegalEntity(
                        text=term,
                        entity_type=category,
                        start_pos=start_pos,
                        end_pos=start_pos + len(term),
                        confidence=0.8,
                        canonical_form=term
                    )
                    entities.append(entity)
        
        # Remove duplicates and sort by position
        entities = self._remove_duplicates(entities)
        entities.sort(key=lambda x: x.start_pos)
        
        return entities
    
    def _get_canonical_form(self, text: str) -> str:
        """Get canonical form of entity"""
        # Expand abbreviations
        for abbr, full_form in self.abbreviations.items():
            if abbr in text:
                return text.replace(abbr, full_form)
        
        # Normalize common variations
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _remove_duplicates(self, entities: List[LegalEntity]) -> List[LegalEntity]:
        """Remove duplicate entities based on text overlap"""
        if not entities:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda x: x.start_pos)
        
        filtered = []
        for entity in entities:
            # Check if this entity overlaps with any existing entity
            is_duplicate = False
            for existing in filtered:
                if self._is_overlapping(entity, existing):
                    # Keep the one with higher confidence
                    if entity.confidence > existing.confidence:
                        filtered.remove(existing)
                        filtered.append(entity)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(entity)
        
        return filtered
    
    def _is_overlapping(self, entity1: LegalEntity, entity2: LegalEntity) -> bool:
        """Check if two entities overlap"""
        return not (entity1.end_pos <= entity2.start_pos or entity2.end_pos <= entity1.start_pos)
    
    def get_legal_references(self, text: str) -> List[str]:
        """
        Extract legal references that can be used for exact lookup
        
        Args:
            text: Input text
            
        Returns:
            List of legal references for exact matching
        """
        references = []
        entities = self.extract_entities(text)
        
        for entity in entities:
            if entity.entity_type in ['law_document', 'procedure', 'visa_type']:
                references.append(entity.canonical_form or entity.text)
        
        return references
    
    def normalize_query(self, query: str) -> str:
        """
        Normalize query for better matching
        
        Args:
            query: Input query
            
        Returns:
            Normalized query string
        """
        # Convert to lowercase
        normalized = query.lower()
        
        # Expand abbreviations
        for abbr, full_form in self.abbreviations.items():
            normalized = normalized.replace(abbr.lower(), full_form.lower())
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove punctuation that might interfere with matching
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        return normalized
    
    def is_legal_query(self, query: str) -> bool:
        """
        Determine if query contains legal entities
        
        Args:
            query: Input query
            
        Returns:
            True if query contains legal entities
        """
        entities = self.extract_entities(query)
        return len(entities) > 0
    
    def get_entity_types(self, query: str) -> Set[str]:
        """
        Get all entity types found in query
        
        Args:
            query: Input query
            
        Returns:
            Set of entity types
        """
        entities = self.extract_entities(query)
        return set(entity.entity_type for entity in entities)