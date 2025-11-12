# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IExtractionStrategy(ABC):
    """Interface for all extraction strategies (ISP - Interface Segregation Principle)"""
    
    @abstractmethod
    def generate_queries(self) -> List[Dict[str, Any]]:
        """
        Generate list of queries to execute
        Returns: List of dicts with 'query' and 'metadata' keys
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate if configuration is valid for this strategy"""
        pass
    
    @abstractmethod
    def estimate_resources(self) -> Dict[str, Any]:
        """Estimate resources needed (threads, memory, etc.)"""
        pass

