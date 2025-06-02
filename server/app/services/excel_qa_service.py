"""
📊 Excel Q&A Service - Fast lookup và search trong Excel Q&A data
Optimized cho speed với caching và indexing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
import pickle
import hashlib
from pathlib import Path
from fuzzywuzzy import fuzz, process
import re
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class MatchType(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"

@dataclass
class QAMatch:
    """Kết quả match từ Excel Q&A"""
    question: str
    answer: str
    confidence: float
    match_type: MatchType
    source_row: int
    keywords_matched: List[str] = None
    metadata: Dict[str, Any] = None

class ExcelQAService:
    """
    Excel Q&A Service - Fast search trong structured Q&A data
    Priority: Exact match → Fuzzy match → Keyword match
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        
        # Cache data structures
        self.qa_dataframes = {}  # Domain -> DataFrame
        self.question_indices = {}  # Domain -> Question index
        self.keyword_indices = {}  # Domain -> Keyword index
        self.answer_cache = {}  # Query hash -> Results
        
        # Search configuration
        self.exact_threshold = 0.95
        self.fuzzy_threshold = 0.75
        self.keyword_threshold = 0.6
        
        # Performance tracking
        self.search_stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "keyword_matches": 0,
            "no_matches": 0
        }
        
        # Precomputed indices
        self.index_cache_dir = self.data_path / "shared" / "qa_indices"
        self.index_cache_dir.mkdir(parents=True, exist_ok=True)

    def load_domain_qa(self, domain: str, force_reload: bool = False) -> pd.DataFrame:
        """
        Load Q&A data for domain với caching
        
        Args:
            domain: Domain name
            force_reload: Force reload from file
            
        Returns:
            DataFrame với Q&A data
        """
        try:
            # Check cache first
            if not force_reload and domain in self.qa_dataframes:
                return self.qa_dataframes[domain]
            
            # Determine file path
            if domain == "shared":
                excel_file = self.data_path / "shared" / "common_qa.xlsx"
            else:
                excel_file = self.data_path / domain / "question.xlsx"
            
            if not excel_file.exists():
                logger.warning(f"Excel file not found: {excel_file}")
                return pd.DataFrame()
            
            # Load Excel file
            df = pd.read_excel(excel_file)
            
            # Validate and clean data
            df = self._validate_and_clean_qa_data(df)
            
            # Cache the dataframe
            self.qa_dataframes[domain] = df
            
            # Build indices
            self._build_indices(domain, df)
            
            logger.info(f"Loaded {len(df)} Q&A pairs for domain: {domain}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Q&A data for {domain}: {e}")
            return pd.DataFrame()

    def search_qa(self, query: str, domain: str, 
                  max_results: int = 5) -> List[QAMatch]:
        """
        Main search method với multiple strategies
        
        Args:
            query: User query
            domain: Domain to search in
            max_results: Maximum results to return
            
        Returns:
            List of QAMatch objects
        """
        try:
            self.search_stats["total_searches"] += 1
            
            # Normalize query
            normalized_query = self._normalize_query(query)
            
            # Check cache
            cache_key = self._get_cache_key(normalized_query, domain)
            if cache_key in self.answer_cache:
                self.search_stats["cache_hits"] += 1
                return self.answer_cache[cache_key]
            
            # Load domain data
            df = self.load_domain_qa(domain)
            if df.empty:
                return []
            
            # Search strategies
            results = []
            
            # 1. Exact match search
            exact_results = self._search_exact_match(normalized_query, df)
            results.extend(exact_results)
            
            # 2. Fuzzy match search (if no exact matches)
            if not exact_results:
                fuzzy_results = self._search_fuzzy_match(normalized_query, df)
                results.extend(fuzzy_results)
            
            # 3. Keyword match search (if insufficient results)
            if len(results) < max_results:
                keyword_results = self._search_keyword_match(normalized_query, df)
                results.extend(keyword_results)
            
            # Remove duplicates based on question text
        seen_questions = set()
        unique_results = []
        
        for result in results:
            question_key = result.question.lower().strip()
            if question_key not in seen_questions:
                seen_questions.add(question_key)
                unique_results.append(result)
        
        # Sort by confidence descending
        unique_results.sort(key=lambda r: r.confidence, reverse=True)
        
        return unique_results

    def _build_indices(self, domain: str, df: pd.DataFrame) -> None:
        """Build search indices for faster lookup"""
        
        try:
            # Question index for fast lookup
            question_index = {}
            keyword_index = defaultdict(list)
            
            for idx, row in df.iterrows():
                question = str(row['question']).strip()
                keywords = self._extract_keywords(question)
                
                # Question index
                question_index[question.lower()] = idx
                
                # Keyword index
                for keyword in keywords:
                    keyword_index[keyword].append(idx)
            
            self.question_indices[domain] = question_index
            self.keyword_indices[domain] = keyword_index
            
            # Cache indices to disk
            self._save_indices_to_cache(domain, question_index, keyword_index)
            
            logger.debug(f"Built indices for {domain}: {len(question_index)} questions, {len(keyword_index)} keywords")
            
        except Exception as e:
            logger.error(f"Error building indices for {domain}: {e}")

    def _save_indices_to_cache(self, domain: str, question_index: Dict, keyword_index: Dict) -> None:
        """Save indices to cache files"""
        
        try:
            cache_file = self.index_cache_dir / f"{domain}_indices.pkl"
            
            cache_data = {
                "question_index": question_index,
                "keyword_index": dict(keyword_index),
                "version": "1.0"
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            logger.warning(f"Could not save indices cache for {domain}: {e}")

    def _load_indices_from_cache(self, domain: str) -> bool:
        """Load indices from cache files"""
        
        try:
            cache_file = self.index_cache_dir / f"{domain}_indices.pkl"
            
            if not cache_file.exists():
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.question_indices[domain] = cache_data["question_index"]
            self.keyword_indices[domain] = defaultdict(list, cache_data["keyword_index"])
            
            return True
            
        except Exception as e:
            logger.warning(f"Could not load indices cache for {domain}: {e}")
            return False

    def _get_available_domains(self) -> List[str]:
        """Get list of available domains"""
        
        domains = []
        
        # Check for shared domain
        shared_file = self.data_path / "shared" / "common_qa.xlsx"
        if shared_file.exists():
            domains.append("shared")
        
        # Check for other domains
        for item in self.data_path.iterdir():
            if item.is_dir() and item.name not in ["shared", "processed"]:
                qa_file = item / "question.xlsx"
                if qa_file.exists():
                    domains.append(item.name)
        
        return domains

    def get_domain_statistics(self, domain: str) -> Dict[str, Any]:
        """Get statistics for domain Q&A data"""
        
        try:
            df = self.load_domain_qa(domain)
            
            if df.empty:
                return {"error": "No data available"}
            
            # Basic statistics
            stats = {
                "total_qa_pairs": len(df),
                "avg_question_length": df['question'].str.len().mean(),
                "avg_answer_length": df['answer'].str.len().mean(),
                "unique_questions": df['question'].nunique()
            }
            
            # Keyword statistics
            all_keywords = []
            for _, row in df.iterrows():
                keywords = self._extract_keywords(str(row['question']))
                all_keywords.extend(keywords)
            
            keyword_counts = defaultdict(int)
            for keyword in all_keywords:
                keyword_counts[keyword] += 1
            
            stats["total_keywords"] = len(keyword_counts)
            stats["top_keywords"] = dict(sorted(keyword_counts.items(), 
                                              key=lambda x: x[1], reverse=True)[:10])
            
            # Domain-specific statistics
            if 'domain' in df.columns:
                stats["domain_distribution"] = df['domain'].value_counts().to_dict()
            
            if 'confidence' in df.columns:
                stats["avg_confidence"] = df['confidence'].mean()
                stats["confidence_distribution"] = {
                    "high (>0.8)": len(df[df['confidence'] > 0.8]),
                    "medium (0.5-0.8)": len(df[(df['confidence'] >= 0.5) & (df['confidence'] <= 0.8)]),
                    "low (<0.5)": len(df[df['confidence'] < 0.5])
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting domain statistics: {e}")
            return {"error": str(e)}

    def update_qa_data(self, domain: str, new_qa_pairs: List[Dict[str, str]]) -> bool:
        """
        Update Q&A data for domain
        
        Args:
            domain: Domain name
            new_qa_pairs: List of {"question": "", "answer": ""} dicts
            
        Returns:
            True if successful
        """
        try:
            # Load existing data
            df = self.load_domain_qa(domain)
            
            # Create new DataFrame from new pairs
            new_df = pd.DataFrame(new_qa_pairs)
            
            # Validate new data
            new_df = self._validate_and_clean_qa_data(new_df)
            
            if new_df.empty:
                return False
            
            # Merge with existing data
            if not df.empty:
                combined_df = pd.concat([df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['question'], keep='last')
            else:
                combined_df = new_df
            
            # Save back to Excel
            if domain == "shared":
                excel_file = self.data_path / "shared" / "common_qa.xlsx"
            else:
                excel_file = self.data_path / domain / "question.xlsx"
            
            excel_file.parent.mkdir(parents=True, exist_ok=True)
            combined_df.to_excel(excel_file, index=False)
            
            # Update cache
            self.qa_dataframes[domain] = combined_df
            self._build_indices(domain, combined_df)
            
            # Clear answer cache for this domain
            keys_to_remove = [k for k in self.answer_cache.keys() if domain in k]
            for key in keys_to_remove:
                del self.answer_cache[key]
            
            logger.info(f"Updated {len(new_qa_pairs)} Q&A pairs for domain {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating Q&A data for {domain}: {e}")
            return False

    def delete_qa_pair(self, domain: str, question: str) -> bool:
        """Delete a Q&A pair by question"""
        
        try:
            df = self.load_domain_qa(domain)
            
            if df.empty:
                return False
            
            # Find and remove the question
            initial_count = len(df)
            df = df[df['question'] != question]
            
            if len(df) == initial_count:
                return False  # Question not found
            
            # Save back to Excel
            if domain == "shared":
                excel_file = self.data_path / "shared" / "common_qa.xlsx"
            else:
                excel_file = self.data_path / domain / "question.xlsx"
            
            df.to_excel(excel_file, index=False)
            
            # Update cache
            self.qa_dataframes[domain] = df
            self._build_indices(domain, df)
            
            # Clear answer cache
            keys_to_remove = [k for k in self.answer_cache.keys() if domain in k]
            for key in keys_to_remove:
                del self.answer_cache[key]
            
            logger.info(f"Deleted Q&A pair for question: {question[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Q&A pair: {e}")
            return False

    def get_similar_questions(self, question: str, domain: str, 
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar questions for suggestion"""
        
        try:
            df = self.load_domain_qa(domain)
            
            if df.empty:
                return []
            
            questions = df['question'].astype(str).tolist()
            
            # Find similar questions using fuzzy matching
            similar = process.extract(question, questions, limit=limit*2)
            
            results = []
            for similar_question, score in similar:
                if score > 50:  # Minimum similarity threshold
                    matching_row = df[df['question'] == similar_question].iloc[0]
                    results.append({
                        "question": similar_question,
                        "answer": matching_row['answer'][:100] + "..." if len(matching_row['answer']) > 100 else matching_row['answer'],
                        "similarity": score / 100
                    })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error getting similar questions: {e}")
            return []

    def rebuild_all_indices(self) -> Dict[str, bool]:
        """Rebuild all indices for all domains"""
        
        results = {}
        domains = self._get_available_domains()
        
        for domain in domains:
            try:
                df = self.load_domain_qa(domain, force_reload=True)
                if not df.empty:
                    self._build_indices(domain, df)
                    results[domain] = True
                else:
                    results[domain] = False
            except Exception as e:
                logger.error(f"Error rebuilding indices for {domain}: {e}")
                results[domain] = False
        
        # Clear answer cache
        self.answer_cache.clear()
        
        logger.info(f"Rebuilt indices for {len(results)} domains")
        return results

    def clear_cache(self) -> Dict[str, int]:
        """Clear all caches"""
        
        cache_sizes = {
            "qa_dataframes": len(self.qa_dataframes),
            "question_indices": len(self.question_indices),
            "keyword_indices": len(self.keyword_indices),
            "answer_cache": len(self.answer_cache)
        }
        
        self.qa_dataframes.clear()
        self.question_indices.clear()
        self.keyword_indices.clear()
        self.answer_cache.clear()
        
        logger.info("Cleared all caches")
        return cache_sizes

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        
        stats = dict(self.search_stats)
        
        # Add cache statistics
        stats["cache_stats"] = {
            "domains_loaded": len(self.qa_dataframes),
            "total_qa_pairs": sum(len(df) for df in self.qa_dataframes.values()),
            "cached_results": len(self.answer_cache),
            "available_domains": len(self._get_available_domains())
        }
        
        # Calculate success rate
        total_searches = stats["total_searches"]
        if total_searches > 0:
            stats["success_rate"] = (total_searches - stats["no_matches"]) / total_searches
            stats["cache_hit_rate"] = stats["cache_hits"] / total_searches
        else:
            stats["success_rate"] = 0
            stats["cache_hit_rate"] = 0
        
        return stats

    def export_qa_data(self, domain: str, format: str = "json") -> Optional[str]:
        """
        Export Q&A data in different formats
        
        Args:
            domain: Domain name
            format: Export format ("json", "csv", "xlsx")
            
        Returns:
            Exported data as string or None if error
        """
        try:
            df = self.load_domain_qa(domain)
            
            if df.empty:
                return None
            
            if format == "json":
                return df.to_json(orient="records", ensure_ascii=False, indent=2)
            elif format == "csv":
                return df.to_csv(index=False)
            elif format == "xlsx":
                # Return path to saved file
                export_file = self.data_path / "exports" / f"{domain}_qa_export.xlsx"
                export_file.parent.mkdir(parents=True, exist_ok=True)
                df.to_excel(export_file, index=False)
                return str(export_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting Q&A data: {e}")
            return None

# Test và example usage
if __name__ == "__main__":
    service = ExcelQAService("data")
    
    # Test domain loading
    domains = service._get_available_domains()
    print(f"✅ Available domains: {domains}")
    
    if domains:
        test_domain = domains[0]
        
        # Test loading
        df = service.load_domain_qa(test_domain)
        print(f"✅ Loaded {len(df)} Q&A pairs for {test_domain}")
        
        # Test searching
        test_queries = [
            "phí làm hộ chiếu",
            "thủ tục cấp căn cước",
            "thời gian làm visa",
            "giấy tờ cần thiết"
        ]
        
        for query in test_queries:
            results = service.search_qa(query, test_domain)
            print(f"\n🔍 Query: {query}")
            print(f"📝 Results: {len(results)}")
            
            for i, result in enumerate(results[:2]):
                print(f"  {i+1}. {result.question[:50]}...")
                print(f"     Confidence: {result.confidence:.2f} ({result.match_type.value})")
        
        # Test statistics
        stats = service.get_domain_statistics(test_domain)
        print(f"\n📊 Domain stats: {stats.get('total_qa_pairs', 0)} pairs")
        
        # Test service stats
        service_stats = service.get_service_stats()
        print(f"📈 Service stats: {service_stats['total_searches']} searches, {service_stats['success_rate']:.2%} success rate")
 và sort by confidence
            results = self._deduplicate_and_sort(results)
            
            # Limit results
            results = results[:max_results]
            
            # Cache results
            self.answer_cache[cache_key] = results
            
            # Update stats
            if results:
                if results[0].match_type == MatchType.EXACT:
                    self.search_stats["exact_matches"] += 1
                elif results[0].match_type == MatchType.FUZZY:
                    self.search_stats["fuzzy_matches"] += 1
                else:
                    self.search_stats["keyword_matches"] += 1
            else:
                self.search_stats["no_matches"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Q&A: {e}")
            return []

    def search_cross_domain(self, query: str, 
                           domains: Optional[List[str]] = None,
                           max_results: int = 5) -> List[QAMatch]:
        """
        Search across multiple domains
        
        Args:
            query: User query
            domains: List of domains to search (None = all available)
            max_results: Maximum results
            
        Returns:
            List of QAMatch objects from all domains
        """
        try:
            if domains is None:
                domains = self._get_available_domains()
            
            all_results = []
            
            for domain in domains:
                domain_results = self.search_qa(query, domain, max_results)
                
                # Add domain penalty for cross-domain results
                for result in domain_results:
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["source_domain"] = domain
                    result.confidence *= 0.9  # Slight penalty for cross-domain
                
                all_results.extend(domain_results)
            
            # Sort by confidence và limit results
            all_results.sort(key=lambda r: r.confidence, reverse=True)
            return all_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in cross-domain search: {e}")
            return []

    def _search_exact_match(self, query: str, df: pd.DataFrame) -> List[QAMatch]:
        """Search for exact matches"""
        
        results = []
        
        for idx, row in df.iterrows():
            question = str(row['question']).strip().lower()
            answer = str(row['answer']).strip()
            
            # Calculate exact match score
            similarity = fuzz.ratio(query.lower(), question) / 100
            
            if similarity >= self.exact_threshold:
                results.append(QAMatch(
                    question=row['question'],
                    answer=answer,
                    confidence=similarity,
                    match_type=MatchType.EXACT,
                    source_row=idx,
                    metadata={
                        "similarity_score": similarity,
                        "match_method": "exact_text_comparison"
                    }
                ))
        
        return results

    def _search_fuzzy_match(self, query: str, df: pd.DataFrame) -> List[QAMatch]:
        """Search using fuzzy matching"""
        
        results = []
        questions = df['question'].astype(str).tolist()
        
        # Use process.extract for efficient fuzzy matching
        matches = process.extract(
            query, 
            questions, 
            limit=10,
            scorer=fuzz.token_sort_ratio
        )
        
        for question, score in matches:
            if score / 100 >= self.fuzzy_threshold:
                # Find corresponding row
                matching_rows = df[df['question'] == question]
                if not matching_rows.empty:
                    row = matching_rows.iloc[0]
                    idx = matching_rows.index[0]
                    
                    results.append(QAMatch(
                        question=question,
                        answer=str(row['answer']).strip(),
                        confidence=score / 100,
                        match_type=MatchType.FUZZY,
                        source_row=idx,
                        metadata={
                            "fuzzy_score": score,
                            "match_method": "token_sort_ratio"
                        }
                    ))
        
        return results

    def _search_keyword_match(self, query: str, df: pd.DataFrame) -> List[QAMatch]:
        """Search using keyword matching"""
        
        results = []
        query_keywords = self._extract_keywords(query)
        
        if not query_keywords:
            return results
        
        for idx, row in df.iterrows():
            question = str(row['question']).strip()
            answer = str(row['answer']).strip()
            
            # Extract keywords from question và answer
            question_keywords = self._extract_keywords(question)
            answer_keywords = self._extract_keywords(answer)
            all_keywords = question_keywords + answer_keywords
            
            # Calculate keyword overlap
            matched_keywords = []
            for qkw in query_keywords:
                for akw in all_keywords:
                    if fuzz.ratio(qkw, akw) > 80:  # Fuzzy keyword matching
                        matched_keywords.append(qkw)
                        break
            
            if matched_keywords:
                # Calculate confidence based on keyword overlap
                confidence = len(matched_keywords) / len(query_keywords)
                
                if confidence >= self.keyword_threshold:
                    results.append(QAMatch(
                        question=question,
                        answer=answer,
                        confidence=confidence,
                        match_type=MatchType.KEYWORD,
                        source_row=idx,
                        keywords_matched=matched_keywords,
                        metadata={
                            "keyword_overlap": len(matched_keywords),
                            "total_query_keywords": len(query_keywords),
                            "match_method": "keyword_overlap"
                        }
                    ))
        
        return results

    def _validate_and_clean_qa_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate và clean Q&A data"""
        
        # Check required columns
        required_columns = ['question', 'answer']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return pd.DataFrame()
        
        # Clean data
        df = df.dropna(subset=required_columns)
        df['question'] = df['question'].astype(str).str.strip()
        df['answer'] = df['answer'].astype(str).str.strip()
        
        # Remove empty entries
        df = df[(df['question'] != '') & (df['answer'] != '')]
        
        # Add optional columns if not present
        if 'keywords' not in df.columns:
            df['keywords'] = df['question'].apply(self._extract_keywords_string)
        
        if 'domain' not in df.columns:
            df['domain'] = 'general'
        
        if 'confidence' not in df.columns:
            df['confidence'] = 1.0
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['question'], keep='first')
        
        return df.reset_index(drop=True)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        # Remove punctuation và lowercase
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = cleaned_text.split()
        
        # Remove stopwords (Vietnamese)
        stopwords = {
            'là', 'của', 'và', 'có', 'được', 'này', 'đó', 'để', 'trong', 'với', 
            'từ', 'trên', 'dưới', 'về', 'như', 'khi', 'nào', 'đâu', 'sao', 
            'gì', 'ai', 'làm', 'thế', 'bao', 'nhiều', 'ở', 'tại', 'theo'
        }
        
        # Filter keywords
        keywords = [word for word in words if len(word) > 2 and word not in stopwords]
        
        return keywords

    def _extract_keywords_string(self, text: str) -> str:
        """Extract keywords as comma-separated string"""
        return ', '.join(self._extract_keywords(text))

    def _normalize_query(self, query: str) -> str:
        """Normalize user query"""
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters but keep Vietnamese
        normalized = re.sub(r'[^\w\s\?]', ' ', normalized)
        
        return normalized.lower()

    def _get_cache_key(self, query: str, domain: str) -> str:
        """Generate cache key for query"""
        return hashlib.md5(f"{query}:{domain}".encode()).hexdigest()

    def _deduplicate_and_sort(self, results: List[QAMatch]) -> List[QAMatch]:
        """Remove duplicates và sort by confidence"""
        
        # Remove duplicates