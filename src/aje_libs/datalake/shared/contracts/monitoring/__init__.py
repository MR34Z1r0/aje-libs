"""
Contratos/Interfaces compartidas para monitoreo
"""
from .monitor_interface import IMonitor
from .event_logger_interface import IEventLogger
from .notification_interface import INotificationService

__all__ = ['IMonitor', 'IEventLogger', 'INotificationService']

