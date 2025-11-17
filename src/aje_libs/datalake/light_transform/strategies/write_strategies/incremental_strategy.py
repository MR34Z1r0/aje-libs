# -*- coding: utf-8 -*-
"""
IncrementalStrategy - Estrategia de escritura para carga incremental (UPSERT/MERGE)
Aplica MERGE/UPSERT para tablas con load_type='incremental'
"""
from typing import List, Optional

from ...contracts.storage.write_strategy_interface import IWriteStrategy
from ....shared.services.logging import LoggerService


class IncrementalStrategy(IWriteStrategy):
    """
    Estrategia para carga incremental.
    Ejecuta MERGE/UPSERT usando columnas ID, o APPEND si no hay columnas ID o es primera carga.
    """
    
    def __init__(self):
        """Inicializa la estrategia incremental"""
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
        Ejecuta operación MERGE/UPSERT o APPEND según disponibilidad
        
        Args:
            data_writer: Instancia de IDataWriter
            df: DataFrame con los datos
            path: Ruta de destino
            partition_cols: Columnas de partición
            **kwargs: Argumentos adicionales:
                - merge_condition: Condición SQL para merge (opcional, se construye si id_columns está disponible)
                - id_columns: Lista de columnas ID para construir merge_condition
                - table_exists: Si la tabla existe (para decidir entre MERGE y APPEND)
                
        Raises:
            ValueError: Si no hay datos para procesar
        """
        # Validación básica
        if df is None or df.isEmpty():
            self.logger.warning("⚠️ DataFrame vacío para estrategia incremental - saltando escritura")
            return
        
        id_columns = kwargs.get('id_columns', [])
        merge_condition = kwargs.get('merge_condition')
        table_exists = kwargs.get('table_exists', False)
        
        records_count = df.count()
        
        # Si hay columnas ID y la tabla existe, usar MERGE
        if id_columns and table_exists:
            # Validar que las columnas ID existan en el DataFrame
            missing_id_cols = [col for col in id_columns if col not in df.columns]
            if missing_id_cols:
                self.logger.warning(
                    f"⚠️ Columnas ID faltantes en DataFrame: {missing_id_cols}. "
                    f"Usando APPEND en lugar de MERGE."
                )
                data_writer.append(df=df, path=path, partition_cols=partition_cols)
                return
            
            if not merge_condition:
                # Construir condición de merge automáticamente
                merge_condition = " AND ".join([f"old.{col} = new.{col}" for col in id_columns])
            
            self.logger.info(
                f"🔄 Ejecutando MERGE incremental: {records_count} registros usando columnas ID: {id_columns}"
            )
            data_writer.merge(
                df=df,
                path=path,
                merge_condition=merge_condition,
                partition_cols=partition_cols
            )
            self.logger.info(f"✅ MERGE incremental completado: {records_count} registros procesados")
        else:
            # Si no hay columnas ID o es primera carga, usar APPEND
            reason = "sin columnas ID" if not id_columns else "tabla no existe (primera carga)"
            self.logger.info(
                f"📝 Ejecutando APPEND incremental ({reason}): {records_count} registros"
            )
            data_writer.append(
                df=df,
                path=path,
                partition_cols=partition_cols
            )
            self.logger.info(f"✅ APPEND incremental completado: {records_count} registros insertados")
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia"""
        return "incremental"
    
    def requires_id_columns(self) -> bool:
        """Esta estrategia puede usar columnas ID pero no es obligatorio"""
        return False  # Opcional: usa MERGE si están disponibles, sino APPEND
    
    def requires_period_column(self) -> bool:
        """Esta estrategia no requiere columna de período"""
        return False


__all__ = ["IncrementalStrategy"]

