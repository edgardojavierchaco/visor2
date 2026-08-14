#services/supervisor_query.py
"""Compatibilidad con imports antiguos.

El servicio canónico es supervisor_query_service.SupervisorQueryService.
"""
from .supervisor_query_service import SupervisorQueryService

__all__ = ["SupervisorQueryService"]
