"""
Motor de transformaciones para light_transform.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.column import Column
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    TimestampType,
)

from aje_libs.datalake.light_transform.contracts.transformation import ITransformationEngine
from aje_libs.datalake.shared.models import ColumnMetadata  # ✅ Movido a shared/models
from aje_libs.datalake.light_transform.services.logging.datalake_logger import DataLakeLogger
from .expression_parser import ExpressionParser


class TransformationException(Exception):
    """Excepción específica para errores de transformación"""

    def __init__(self, column_name: str, message: str):
        self.column_name = column_name
        self.message = message
        super().__init__(f"Error en columna {column_name}: {message}")


class TransformationWarningException(Exception):
    """Excepción para transformaciones completadas con advertencias"""

    def __init__(self, warnings: List[str], message: str):
        self.warnings = warnings
        self.message = message
        super().__init__(message)


class TransformationEngine(ITransformationEngine):
    """Motor de transformaciones optimizado con soporte para funciones anidadas"""

    MAGIC_OFFSET = 693596

    def __init__(self, spark_session):
        self.spark = spark_session
        self.parser = ExpressionParser()
        self.logger = DataLakeLogger.get_logger(__name__)

    def apply_transformations(self, df, columns_metadata: List[ColumnMetadata]) -> Tuple[Any, List[str]]:
        """
        Aplica todas las transformaciones de manera optimizada con soporte para funciones anidadas
        Retorna (DataFrame transformado, lista de errores)
        """
        errors: List[str] = []
        transformation_exprs: List[Column] = []

        sorted_columns = sorted(columns_metadata, key=lambda x: x.column_id)

        for column_meta in sorted_columns:
            try:
                expr = self._build_transformation_expression(column_meta, df)
                if expr is not None:
                    transformation_exprs.append(expr.alias(column_meta.name))
                else:
                    if column_meta.transformation and column_meta.transformation.strip():
                        transformation_exprs.append(F.col(column_meta.transformation).alias(column_meta.name))
                    else:
                        spark_type = self._get_spark_type(column_meta.data_type)
                        transformation_exprs.append(F.lit(None).cast(spark_type).alias(column_meta.name))
            except Exception as exc:
                error_msg = f"Error en columna {column_meta.name}: {exc}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                spark_type = self._get_spark_type(column_meta.data_type)
                transformation_exprs.append(F.lit(None).cast(spark_type).alias(column_meta.name))

        transformed_df = df.select(*transformation_exprs) if transformation_exprs else df
        return transformed_df, errors

    def _build_transformation_expression(self, column_meta: ColumnMetadata, df):
        """Construye expresión de transformación para una columna con soporte para funciones anidadas"""
        functions_with_params = self.parser.parse_transformation(column_meta.transformation)

        if not functions_with_params:
            return None

        if len(functions_with_params) == 1 and functions_with_params[0][0] == 'simple_column':
            column_name = functions_with_params[0][1][0] if functions_with_params[0][1] else column_meta.name
            return F.col(column_name)

        function_name, params = functions_with_params[0]
        return self._create_transformation_expr_with_nesting(function_name, params, column_meta.data_type, df)

    def _create_transformation_expr_with_nesting(self, function_name: str, params: List[str], data_type: str, df):
        """Crea expresión de transformación con soporte para funciones anidadas"""
        self.logger.info(f"Aplicando transformación: {function_name} con parámetros: {params}")

        processed_params: List[Any] = []

        for param in params:
            param = param.strip()

            if param.startswith('fn_transform_'):
                nested_functions = self.parser.parse_transformation(param)
                if nested_functions and nested_functions[0][0] != 'simple_column':
                    nested_function_name, nested_params = nested_functions[0]
                    nested_type = self._infer_function_return_type(nested_function_name)
                    nested_expr = self._create_transformation_expr_with_nesting(
                        nested_function_name,
                        nested_params,
                        nested_type,
                        df
                    )
                    processed_params.append(nested_expr)
                else:
                    processed_params.append(F.lit(param))
            else:
                if param in df.columns:
                    processed_params.append(F.col(param))
                else:
                    processed_params.append(param)

        return self._apply_transformation_function(function_name, processed_params, data_type)

    def _infer_function_return_type(self, function_name: str) -> str:
        """Infiere el tipo de retorno de una función de transformación"""
        type_mapping = {
            'fn_transform_Date': 'date',
            'fn_transform_DateMagic': 'date',
            'fn_transform_DatetimeMagic': 'timestamp',
            'fn_transform_Datetime': 'timestamp',
            'fn_transform_Integer': 'integer',
            'fn_transform_Double': 'double',
            'fn_transform_Numeric': 'double',
            'fn_transform_Boolean': 'boolean',
            'fn_transform_PeriodMagic': 'string',
            'fn_transform_ByteMagic': 'string',
            'fn_transform_ClearString': 'string',
            'fn_transform_Concatenate': 'string',
            'fn_transform_Concatenate_ws': 'string',
            'fn_transform_Date_to_String': 'string',
            'fn_transform_Case': 'string',
            'fn_transform_Case_with_default': 'string',
        }
        return type_mapping.get(function_name, 'string')

    def _handle_magic_date(self, origin_param, date_format_param, default_value):
        if isinstance(origin_param, str):
            origin_param = F.col(origin_param)

        date_format_str = date_format_param if isinstance(date_format_param, str) else 'yyyy-MM-dd'

        if isinstance(default_value, str):
            default_value_lit = F.lit(None).cast(DateType()) if default_value.lower() == 'to_null' else F.lit(default_value)
        else:
            default_value_lit = default_value

        magic_date_expr = F.date_add(
            F.to_date(F.lit('1900-01-01')),
            (origin_param.cast(IntegerType()) - F.lit(self.MAGIC_OFFSET))
        )

        format_mapping = {
            'yyyy-MM-dd': 'yyyy-MM-dd',
            'yyyyMMdd': 'yyyyMMdd',
            'dd/MM/yyyy': 'dd/MM/yyyy',
            'MM/dd/yyyy': 'MM/dd/yyyy'
        }
        spark_format = format_mapping.get(date_format_str, 'yyyy-MM-dd')

        default_to_use = default_value_lit if isinstance(default_value, str) and default_value.lower() != 'to_null' else F.lit(None).cast(DateType())

        return F.when(
            origin_param.isNull(),
            default_to_use
        ).when(
            origin_param.cast(IntegerType()).isNotNull() & (origin_param.cast(IntegerType()) > F.lit(100000)),
            magic_date_expr
        ).otherwise(
            F.coalesce(
                F.to_date(origin_param.cast(StringType()), spark_format),
                default_to_use
            )
        )

    def _apply_transformation_function(self, function_name: str, params: List[Any], data_type: str):
        if function_name == 'fn_transform_Concatenate':
            spark_params = []
            for param in params:
                spark_params.append(F.lit(param) if isinstance(param, str) else param)

            return F.concat_ws("|", *[
                F.coalesce(
                    F.when(p.isNull(), F.lit("")).otherwise(
                        F.when(F.trim(p.cast(StringType())) == "", F.lit("")).otherwise(F.trim(p.cast(StringType())))
                    ) if hasattr(p, 'isNull') else F.lit(str(p)),
                    F.lit("")
                )
                for p in spark_params
            ])

        if function_name == 'fn_transform_ClearString':
            if not params:
                raise TransformationException("fn_transform_ClearString", "Requiere nombre de columna")
            origin_param = params[0]

            if isinstance(origin_param, str):
                origin_param = F.col(origin_param)

            if len(params) > 1:
                default = params[1]
                if isinstance(default, str) and default.startswith('$'):
                    default_expr = F.lit(default[1:])
                elif isinstance(default, str):
                    default_expr = F.col(default)
                else:
                    default_expr = default

                return F.when(
                    origin_param.isNull() |
                    (F.trim(origin_param) == "") |
                    (F.trim(origin_param).isin(["None", "NULL", "null"])),
                    default_expr
                ).otherwise(F.trim(origin_param))

            return F.when(
                origin_param.isNull() |
                (F.trim(origin_param) == "") |
                (F.trim(origin_param).isin(["None", "NULL", "null"])),
                F.lit(None).cast(StringType())
            ).otherwise(F.trim(origin_param))

        if function_name == 'fn_transform_DateMagic':
            if len(params) < 2:
                raise TransformationException("fn_transform_DateMagic", "Requiere al menos 2 parámetros")
            origin_param = params[0]
            date_format_param = params[1]
            default_value = params[2] if len(params) > 2 else 'to_null'
            return self._handle_magic_date(origin_param, date_format_param, default_value)

        if function_name == 'fn_transform_Concatenate_ws':
            if len(params) < 2:
                raise TransformationException("fn_transform_Concatenate_ws", "Requiere al menos 2 parámetros")

            separator = params[-1] if isinstance(params[-1], str) else "|"
            columns_to_concat = params[:-1]

            spark_params = []
            for param in columns_to_concat:
                spark_params.append(F.col(param) if isinstance(param, str) else param)

            return F.concat_ws(separator, *[F.coalesce(F.trim(c.cast(StringType())), F.lit("")) for c in spark_params])

        if function_name in ['fn_transform_Integer', 'fn_transform_Double', 'fn_transform_Numeric', 'fn_transform_Boolean']:
            if not params:
                raise TransformationException(function_name, "Requiere nombre de columna")

            origin_param = params[0]
            if isinstance(origin_param, str):
                origin_param = F.col(origin_param)

            type_map = {
                'fn_transform_Integer': IntegerType(),
                'fn_transform_Double': DoubleType(),
                'fn_transform_Boolean': BooleanType()
            }

            if function_name == 'fn_transform_Numeric':
                target_type = self._parse_decimal_type(data_type)
            else:
                target_type = type_map[function_name]

            return F.coalesce(origin_param.cast(target_type), F.lit(None).cast(target_type))

        if function_name == 'fn_transform_Datetime':
            if not params:
                return F.current_timestamp()
            origin_param = params[0] if not isinstance(params[0], str) else F.col(params[0])
            return F.coalesce(F.to_timestamp(origin_param), F.lit(None).cast(TimestampType()))

        if function_name == 'fn_transform_DatetimeMagic':
            return self._apply_datetime_magic(params)

        if function_name == 'fn_transform_Date_to_String':
            if len(params) < 2:
                raise TransformationException("fn_transform_Date_to_String", "Requiere 2 parámetros")

            date_param = params[0]
            format_param = params[1] if isinstance(params[1], str) else 'yyyyMM'

            if isinstance(date_param, str):
                date_param = F.to_date(F.lit(date_param))
            else:
                date_param = F.to_date(date_param)

            return F.date_format(date_param, format_param)

        if function_name == 'fn_transform_Date':
            if len(params) < 2:
                raise TransformationException("fn_transform_Date", "Requiere al menos 2 parámetros")

            origin_param = params[0]
            date_format_param = params[1]
            default_value = params[2] if len(params) > 2 else 'to_null'
            return self._handle_standard_date(origin_param, date_format_param, default_value)

        if function_name == 'fn_transform_PeriodMagic':
            if len(params) < 2:
                raise TransformationException("fn_transform_PeriodMagic", "Requiere 2 parámetros: period, ejercicio")

            period_param = params[0]
            ejercicio_param = params[1]

            if isinstance(period_param, str):
                period_param = F.col(period_param)
            if isinstance(ejercicio_param, str):
                ejercicio_param = F.col(ejercicio_param)

            return F.when(
                period_param.isNull() | ejercicio_param.isNull(),
                F.lit('190001')
            ).otherwise(
                F.concat(
                    ejercicio_param.cast(StringType()),
                    F.lpad(period_param.cast(StringType()), 2, '0')
                )
            )

        if function_name == 'fn_transform_ByteMagic':
            if len(params) < 1:
                raise TransformationException("fn_transform_ByteMagic", "Requiere al menos 1 parámetro")

            origin_param = params[0]
            default_value = params[1] if len(params) > 1 else '$F'

            if isinstance(origin_param, str):
                origin_param = F.col(origin_param)

            if isinstance(default_value, str) and default_value.startswith('$'):
                default_lit = F.lit(default_value[1:])
            elif isinstance(default_value, str):
                default_lit = F.col(default_value)
            else:
                default_lit = default_value

            return F.when(origin_param.isNull(), default_lit) \
                .when(origin_param == F.lit('T'), F.lit('T')) \
                .when(origin_param == F.lit('F'), F.lit('F')) \
                .when(origin_param.cast(StringType()) == '0x54', F.lit('T')) \
                .when(origin_param.cast(StringType()) == '0x46', F.lit('F')) \
                .when(origin_param == F.lit(84), F.lit('T')) \
                .when(origin_param == F.lit(70), F.lit('F')) \
                .otherwise(default_lit)

        if function_name == 'fn_transform_Case':
            return self._apply_case(params, with_default=False)

        if function_name == 'fn_transform_Case_with_default':
            return self._apply_case(params, with_default=True)

        raise TransformationException(function_name, f"Función no soportada: {function_name}")

    def _apply_datetime_magic(self, params: List[Any]):
        if len(params) < 3:
            raise TransformationException("fn_transform_DatetimeMagic", "Requiere al menos 3 parámetros")

        date_param = params[0]
        time_param = params[1]
        format_param = params[2] if isinstance(params[2], str) else 'yyyy-MM-dd HH:mm:ss'
        default_value = params[3] if len(params) > 3 else 'to_null'

        if isinstance(date_param, str):
            date_param = F.col(date_param)
        if isinstance(time_param, str):
            time_param = F.col(time_param)

        date_from_magic = F.date_add(
            F.to_date(F.lit('1900-01-01')),
            (date_param.cast(IntegerType()) - F.lit(self.MAGIC_OFFSET))
        )

        date_from_string = F.to_date(date_param.cast(StringType()), 'yyyy-MM-dd')

        converted_date = F.when(
            date_param.isNull(),
            F.lit(None).cast(DateType())
        ).when(
            date_param.cast(IntegerType()).isNotNull() & (date_param.cast(IntegerType()) > F.lit(100000)),
            date_from_magic
        ).otherwise(
            date_from_string
        )

        time_normalized = F.lpad(time_param.cast(StringType()), 6, '0')

        hours = F.substring(time_normalized, 1, 2)
        minutes = F.substring(time_normalized, 3, 2)
        seconds = F.substring(time_normalized, 5, 2)

        time_string = F.concat_ws(':', hours, minutes, seconds)

        datetime_string = F.concat(
            converted_date.cast(StringType()),
            F.lit(' '),
            time_string
        )

        result_timestamp = F.to_timestamp(datetime_string, 'yyyy-MM-dd HH:mm:ss')

        if isinstance(default_value, str) and default_value.lower() == 'to_null':
            return F.coalesce(
                result_timestamp,
                F.lit(None).cast(TimestampType())
            )

        return F.coalesce(
            result_timestamp,
            F.to_timestamp(F.lit(default_value), 'yyyy-MM-dd HH:mm:ss')
        )

    def _handle_standard_date(self, origin_param, date_format_param, default_value):
        if isinstance(origin_param, str):
            origin_param = F.col(origin_param)

        date_format_str = date_format_param if isinstance(date_format_param, str) else 'yyyy-MM-dd'

        format_mapping = {
            'yyyy-MM-dd': 'yyyy-MM-dd',
            'yyyyMMdd': 'yyyyMMdd',
            'dd/MM/yyyy': 'dd/MM/yyyy',
            'MM/dd/yyyy': 'MM/dd/yyyy'
        }
        spark_format = format_mapping.get(date_format_str, 'yyyy-MM-dd')

        if isinstance(default_value, str):
            if default_value.lower() == 'to_null':
                default_value_lit = F.lit(None).cast(DateType())
            else:
                default_value_lit = F.to_date(F.lit(default_value), 'yyyy-MM-dd')
        else:
            default_value_lit = default_value

        return F.when(
            origin_param.isNull(),
            default_value_lit
        ).otherwise(
            F.coalesce(
                F.to_date(origin_param.cast(StringType()), spark_format),
                default_value_lit
            )
        )

    def _apply_case(self, params: List[Any], with_default: bool):
        if len(params) < 2:
            raise TransformationException(
                "fn_transform_Case_with_default" if with_default else "fn_transform_Case",
                "Requiere al menos 2 parámetros"
            )

        origin_param = params[0]
        if isinstance(origin_param, str):
            origin_param = F.col(origin_param)

        rules = params[1:-1] if with_default and len(params) > 2 else params[1:]
        default_value = params[-1] if with_default else origin_param

        if with_default:
            if isinstance(default_value, str) and default_value.startswith('$'):
                case_expr = F.lit(default_value[1:])
            elif isinstance(default_value, str):
                case_expr = F.col(default_value)
            else:
                case_expr = default_value
        else:
            case_expr = origin_param

        for rule in rules:
            if isinstance(rule, str) and '->' in rule:
                value_case, label_case = rule.split('->')
                values_to_change = [value.strip() for value in value_case.split('|')]

                case_expr = F.when(
                    origin_param.isin(values_to_change),
                    F.lit(label_case.strip())
                ).otherwise(case_expr)

        return case_expr

    def _get_spark_type(self, data_type: str):
        type_mapping = {
            'string': StringType(),
            'int': IntegerType(),
            'integer': IntegerType(),
            'double': DoubleType(),
            'float': DoubleType(),
            'boolean': BooleanType(),
            'timestamp': TimestampType(),
            'date': DateType()
        }

        if isinstance(data_type, str) and 'numeric' in data_type.lower():
            return self._parse_decimal_type(data_type)

        return type_mapping.get(data_type.lower(), StringType())

    def _parse_decimal_type(self, data_type: str):
        import re

        match = re.search(r'numeric\((\d+),(\d+)\)', data_type.lower())
        if match:
            precision = int(match.group(1))
            scale = int(match.group(2))
            return DecimalType(precision, scale)
        return DecimalType(18, 2)

    def apply_post_processing(self, df, columns_metadata: List[ColumnMetadata]):
        id_columns = [col.name for col in columns_metadata if col.is_id]
        filter_date_columns = [col.name for col in columns_metadata if col.is_filter_date]
        order_by_columns = [col.name for col in columns_metadata if col.is_order_by]

        if filter_date_columns and id_columns:
            window_spec = Window.partitionBy(*id_columns).orderBy(*[F.col(c).desc() for c in filter_date_columns])
            df = df.withColumn("row_number", F.row_number().over(window_spec))
            df = df.filter(F.col("row_number") == 1).drop("row_number")

        if order_by_columns:
            df = df.orderBy(*order_by_columns)

        return df


__all__ = ["TransformationEngine", "TransformationException", "TransformationWarningException"]

