# -*- coding: utf-8 -*-
"""
Interface para formatters de datos (ISP - Interface Segregation Principle)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class IFormatter(ABC):
    """Interface para todos los formatters de datos"""
    
    @abstractmethod
    def format_dataframe(self, df: pd.DataFrame, **kwargs) -> bytes:
        """
        Formatea un DataFrame a bytes
        
        Args:
            df: DataFrame a formatear
            **kwargs: Opciones adicionales de formateo
            
        Returns:
            Datos formateados como bytes
        """
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Retorna la extensión de archivo para este formatter
        
        Returns:
            Extensión de archivo (ej: '.csv', '.parquet')
        """
        pass
    
    @abstractmethod
    def get_content_type(self) -> str:
        """
        Retorna el Content-Type para este formatter
        
        Returns:
            Content-Type (ej: 'text/csv', 'application/parquet')
        """
        pass

