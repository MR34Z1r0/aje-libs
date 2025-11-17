# -*- coding: utf-8 -*-
"""
FullLoadStrategy - Estrategia de escritura para carga completa (OVERWRITE)
Aplica OVERWRITE para tablas con load_type='full'
"""
from typing import List, Optional

from ...contracts.storage.write_strategy_interface import IWriteStrategy
from ....shared.services.logging import LoggerService


class FullLoadStrategy(IWriteStrategy):
    """
    Estrategia para carga completa.
    Ejecuta OVERWRITE en el destino, reemplazando todos los datos existentes.
    """
    
    def __init__(self):
        """Inicializa la estrategia full load"""
        self.logger = LoggerService.get_logger(__name__)
    
    def execute(
        self,
        data_writer,
        df,
        path: str,
        partition_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Ejecuta operación OVERWRITE
        
        Args:
            data_writer: Instancia de IDataWriter
            df: DataFrame con los datos
            path: Ruta de destino
            partition_cols: Columnas de partición
            **kwargs: Argumentos adicionales (no usados en esta estrategia)
            
        Raises:
            ValueError: Si no hay datos para procesar
        """
        # Validación básica
        if df is None:
            raise ValueError("DataFrame no puede ser None para estrategia full load")
        
        records_count = df.count()
        
        if records_count == 0:
            self.logger.warning(
                "⚠️ DataFrame vacío para estrategia full load. "
                "Se sobrescribirá la tabla con una tabla vacía."
            )
        else:
            self.logger.info(
                f"📦 Ejecutando FULL LOAD (OVERWRITE): {records_count} registros"
            )
        
        data_writer.overwrite(
            df=df,
            path=path,
            partition_cols=partition_cols
        )
        
        self.logger.info(
            f"✅ FULL LOAD completado: {records_count} registros escritos en {path}"
        )
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia"""
        return "full_load"
    
    def requires_id_columns(self) -> bool:
        """Esta estrategia no requiere columnas ID"""
        return False
    
    def requires_period_column(self) -> bool:
        """Esta estrategia no requiere columna de período"""
        return False


__all__ = ["FullLoadStrategy"]

