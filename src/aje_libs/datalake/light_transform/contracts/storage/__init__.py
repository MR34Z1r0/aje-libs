from aje_libs.datalake.shared.contracts.storage import IDataWriter
from .write_strategy_interface import IWriteStrategy  # ✅ Interface para estrategias de escritura

__all__ = [
    "IDataWriter",
    "IWriteStrategy",  # ✅ Interface para estrategias de escritura
]
