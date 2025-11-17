# strategies/base/extraction_strategy.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .strategy_types import ExtractionStrategyType
from ....shared.models import TableConfig, ExtractionParams  # ✅ ExtractionParams movido a shared/models
from ...models.extraction_config import ExtractionConfig
from ....shared.contracts.watermark import IWatermarkStorage

class ExtractionStrategy(ABC):
    """Estrategia base simplificada para extracción de datos"""
    
    def __init__(self, table_config: TableConfig, extraction_config: ExtractionConfig, watermark_storage: IWatermarkStorage = None):
        self.table_config = table_config
        self.extraction_config = extraction_config
        self.watermark_storage = watermark_storage
        self._validated = False
    
    @abstractmethod
    def build_extraction_params(self) -> ExtractionParams:
        """Construye los parámetros de extracción específicos para esta estrategia"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Valida que la estrategia pueda ejecutarse con la configuración actual"""
        pass
    
    @abstractmethod
    def get_strategy_type(self) -> ExtractionStrategyType:
        """Retorna el tipo de estrategia"""
        pass
    
    @property
    def strategy_name(self) -> str:
        """Nombre de la estrategia para logging"""
        return self.__class__.__name__.replace('Strategy', '').lower()
    
    def validate_and_cache(self) -> bool:
        """Valida y cachea el resultado"""
        if not self._validated:
            self._validated = self.validate()
        return self._validated
    
    def estimate_resources(self) -> Dict[str, Any]:
        """Estima recursos necesarios (implementación por defecto)"""
        return {
            'estimated_threads': 1,
            'estimated_memory_mb': 500,
            'supports_chunking': False,
            'parallel_safe': True
        }
    
    # Métodos helper comunes
    def _parse_columns(self) -> List[str]:
        """Parse column string or list into list"""
        columns = []
        
        # 1. Procesar ID_COLUMN primero si existe
        id_column_processed = self._process_id_column()
        if id_column_processed:
            columns.append(id_column_processed)
        
        # 2. Procesar las columnas regulares
        # Manejar tanto lista como string
        if isinstance(self.table_config.columns, list):
            # Si ya es una lista, usar directamente
            for col in self.table_config.columns:
                if col and col.strip():
                    columns.append(col.strip())
        elif isinstance(self.table_config.columns, str):
            # Si es string, separar por comas
            if self.table_config.columns.strip() == '':
                if not id_column_processed:  # Solo agregar '*' si no hay ID_COLUMN
                    columns.append('*')
            else:
                for col in self.table_config.columns.split(','):
                    clean_col = col.strip()
                    if clean_col:
                        columns.append(clean_col)
        else:
            # Si está vacío o es None, usar '*'
            if not id_column_processed:
                columns.append('*')
        
        return columns if columns else ['*']
    
    def _process_id_column(self) -> str:
        """Process ID_COLUMN with validation logic"""
        # Verificar si ID_COLUMN tiene valor
        if not hasattr(self.table_config, 'id_column') or not self.table_config.id_column:
            return None
        
        id_column = self.table_config.id_column.strip()
        if not id_column:
            return None
        
        # Verificar si 'id' ya existe en COLUMNS
        if self._check_id_exists_in_columns():
            return None
        
        # Retornar ID_COLUMN con alias 'id'
        return f"{id_column} as id"

    def _check_id_exists_in_columns(self) -> bool:
        """Check if 'id' keyword exists in columns (string or list)"""
        if not self.table_config.columns:
            return False
        
        import re
        
        # Manejar tanto lista como string
        if isinstance(self.table_config.columns, list):
            # Si es lista, buscar 'id' directamente
            for col in self.table_config.columns:
                if col and col.strip().lower() == 'id':
                    return True
            return False
        elif isinstance(self.table_config.columns, str):
            # Si es string, usar regex como antes
            columns_str = self.table_config.columns.lower().strip()
            
            # Patrones para detectar 'id' como columna independiente
            id_patterns = [
                r'^\s*id\s*$',           # Solo 'id'
            ]
            
            # Verificar cada patrón
            for pattern in id_patterns:
                if re.search(pattern, columns_str):
                    return True
        
        return False

    def _get_source_table_name(self) -> str:
        """Obtiene el nombre de la tabla fuente limpio"""
        source_table = self.table_config.source_table or self.extraction_config.table_name
        # Remover alias (texto después del primer espacio)
        if source_table and ' ' in source_table:
            return source_table.split()[0]
        return source_table
    
    def _build_table_name_with_joins(self) -> str:
        """Construye el nombre de tabla con schema, preservando alias si existe, y agregando JOINs"""
        source_table = self.table_config.source_table or ""
        source_schema = self.table_config.source_schema or ""
        
        # Detectar alias necesario basándose en las columnas
        required_alias = self._detect_required_table_alias()
        
        # Verificar si source_table ya tiene un alias
        source_table_has_alias = ' ' in source_table.strip()
        existing_alias = None
        if source_table_has_alias:
            parts = source_table.strip().split(None, 1)
            if len(parts) > 1:
                existing_alias = parts[1].strip()
        
        # Construir table name preservando alias si existe, o agregando el detectado
        if '.' in source_table and not source_schema:
            # Ya tiene schema, usar tal cual (puede incluir alias)
            table_name_with_joins = source_table.strip()
        elif source_schema:
            # Construir con schema
            if source_table_has_alias:
                # Si source_table ya tiene alias, preservarlo
                table_name_only = source_table.strip().split(None, 1)[0]
                table_name_with_joins = f"{source_schema}.{table_name_only} {existing_alias}".strip()
            else:
                table_name_with_joins = f"{source_schema}.{source_table}".strip()
        else:
            # Sin schema, usar solo la tabla
            table_name_with_joins = source_table.strip()
        
        # Si las columnas requieren un alias pero la tabla no lo tiene, agregarlo
        if required_alias and not source_table_has_alias and ' ' not in table_name_with_joins:
            # Extraer solo el nombre de tabla sin schema para agregar alias
            table_name_only = table_name_with_joins
            if '.' in table_name_with_joins:
                table_name_only = table_name_with_joins.split('.')[-1]
                schema_part = table_name_with_joins.rsplit('.', 1)[0]
                table_name_with_joins = f"{schema_part}.{table_name_only} {required_alias}"
            else:
                table_name_with_joins = f"{table_name_with_joins} {required_alias}"
        
        # Agregar JOINs si existen
        if hasattr(self.table_config, 'join_expr') and self.table_config.join_expr and self.table_config.join_expr.strip():
            table_name_with_joins += f" {self.table_config.join_expr.strip()}"
        
        return table_name_with_joins
    
    def _detect_required_table_alias(self) -> str:
        """Detecta el alias de tabla necesario basándose en las columnas"""
        import re
        
        # Obtener todas las columnas como string
        columns_str = ""
        if isinstance(self.table_config.columns, list):
            columns_str = ' '.join(self.table_config.columns)
        elif isinstance(self.table_config.columns, str):
            columns_str = self.table_config.columns
        
        # También incluir ID_COLUMN si existe
        if hasattr(self.table_config, 'id_column') and self.table_config.id_column:
            columns_str += f" {self.table_config.id_column}"
        
        # Buscar patrones de alias como "m.columna" o "t.columna"
        # El alias más común será el principal
        alias_pattern = r'\b([a-z])\.([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(alias_pattern, columns_str, re.IGNORECASE)
        
        if matches:
            # Contar frecuencia de cada alias
            alias_counts = {}
            for alias, _ in matches:
                alias = alias.lower()
                alias_counts[alias] = alias_counts.get(alias, 0) + 1
            
            # Retornar el alias más común (probablemente 'm' para la tabla principal)
            if alias_counts:
                most_common_alias = max(alias_counts.items(), key=lambda x: x[1])[0]
                return most_common_alias
        
        return None
    
    def _build_basic_metadata(self) -> Dict[str, Any]:
        """Construye metadatos básicos para la extracción"""
        return {
            'strategy': self.strategy_name,
            'table_name': self.extraction_config.table_name,
            'source_table': self._get_source_table_name(),
            'load_type': self.table_config.load_type,
            'timestamp': self.extraction_config.execution_timestamp
        }