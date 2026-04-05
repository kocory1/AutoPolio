"""
RAG(Related-Augmented Generation) 서비스 패키지.

User Asset 및 합격 자소서 VectorDB를 조회해 Writer/Inspector/Job Fit에서
재사용 가능한 검색 함수 제공
"""

from .passed_samples import retrieve_passed_cover_letters
from .user_assets import retrieve_user_assets

__all__ = ["retrieve_passed_cover_letters", "retrieve_user_assets"]
