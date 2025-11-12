"""
Parser de expresiones de transformación - Implementa parsing de expresiones con funciones anidadas (SRP)
"""
import re
from typing import List, Tuple


class ExpressionParser:
    """
    Parser robusto para expresiones de transformación con soporte para funciones anidadas (SRP)
    """
    
    def __init__(self):
        self.function_pattern = re.compile(r'(\w+)\((.*)\)$')
    
    def parse_transformation(self, expression: str) -> List[Tuple[str, List[str]]]:
        """
        Parsea expresión de transformación y retorna lista de (función, parámetros)
        Soporta funciones anidadas
        
        Args:
            expression: Expresión de transformación (ej: "fn_transform_upper(fn_transform_trim(columna))")
            
        Returns:
            Lista de tuplas (nombre_función, [parámetros])
        """
        if not expression or expression.strip() == '':
            return []
        
        functions_with_params = []
        remaining = expression.strip()
        
        match = self.function_pattern.match(remaining)
        if not match:
            # No es una función, es una columna simple
            return [('simple_column', [remaining])]
        
        function_name = match.group(1)
        params_str = match.group(2)
        
        # Extraer parámetros (que pueden contener funciones anidadas)
        params = self._extract_parameters(params_str) if params_str else []
        functions_with_params.append((function_name, params))
        
        return functions_with_params
    
    def _extract_parameters(self, params_str: str) -> List[str]:
        """
        Extrae parámetros de una función manejando:
        - Comas en strings
        - Paréntesis anidados (para funciones anidadas)
        - Comillas
        
        Args:
            params_str: String con parámetros
            
        Returns:
            Lista de parámetros extraídos
        """
        if not params_str:
            return []
        
        params = []
        current_param = ""
        paren_count = 0
        in_quotes = False
        
        i = 0
        while i < len(params_str):
            char = params_str[i]
            
            if char == '"' and (i == 0 or params_str[i-1] != '\\'):
                in_quotes = not in_quotes
                current_param += char
            elif char == '(' and not in_quotes:
                paren_count += 1
                current_param += char
            elif char == ')' and not in_quotes:
                paren_count -= 1
                current_param += char
            elif char == ',' and paren_count == 0 and not in_quotes:
                # Coma a nivel raíz, es separador de parámetros
                if current_param.strip():
                    params.append(current_param.strip())
                current_param = ""
            else:
                current_param += char
            
            i += 1
        
        # Agregar último parámetro
        if current_param.strip():
            params.append(current_param.strip())
        
        return params

