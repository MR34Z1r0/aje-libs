# -*- coding: utf-8 -*-
"""
Interface para estrategias de escritura (ISP - Interface Segregation Principle)
Define el contrato para ejecutar diferentes estrategias de escritura según load_type
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IWriteStrategy(ABC):
    """
    Contrato para estrategias de escritura que implementan diferentes operaciones
    según el tipo de carga (full, incremental, time_range).
    """
    
    @abstractmethod
    def execute(
        self,
        data_writer,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Ejecuta la operación de escritura según la estrategia
        
        Args:
            data_writer: Instancia de IDataWriter (DeltaTableWriter, IcebergTableWriter, etc.)
            df: DataFrame con los datos a escribir
            path: Ruta de destino
            partition_cols: Columnas de partición (opcional)
            **kwargs: Argumentos adicionales específicos de la estrategia:
                - merge_condition: Para estrategias incremental
                - time_range_config: Para estrategias time_range
                - id_columns: Columnas ID para merge
                - period_column: Columna de período para time_range
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia"""
        pass
    
    @abstractmethod
    def requires_id_columns(self) -> bool:
        """Indica si la estrategia requiere columnas ID"""
        pass
    
    @abstractmethod
    def requires_period_column(self) -> bool:
        """Indica si la estrategia requiere columna de período"""
        pass

