from typing import List
from schemas.search_result import SearchResult

def extract_urls(results: List[SearchResult]) -> List:
    return [result.url for result in results] 