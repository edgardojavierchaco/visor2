from copy import deepcopy
from django.forms.models import model_to_dict


class ChangeTracker:
    """
    Tracker inteligente de cambios entre estados de modelos.

    Objetivo:
    - Comparar snapshots de objetos
    - Detectar diferencias campo a campo
    - Normalizar valores para auditoría
    """

    def __init__(self, instance):
        self.instance = instance

    # --------------------------------------
    # SERIALIZACIÓN
    # --------------------------------------

    def serialize(self):
        """
        Convierte instancia Django en dict plano.
        """
        return model_to_dict(self.instance)

    def serialize_from_dict(self, data):
        """
        Normaliza dict externo (snapshot previo).
        """
        return deepcopy(data or {})

    # --------------------------------------
    # DIFF PRINCIPAL
    # --------------------------------------

    def diff(self, old_data, new_data=None):
        """
        Devuelve lista de cambios detectados.
        """

        if new_data is None:
            new_data = self.serialize()

        old_data = self.serialize_from_dict(old_data)

        changes = []

        all_keys = set(old_data.keys()) | set(new_data.keys())

        for key in all_keys:
            old_value = old_data.get(key)
            new_value = new_data.get(key)

            if self._has_changed(old_value, new_value):
                changes.append({
                    "field": key,
                    "old": self._normalize(old_value),
                    "new": self._normalize(new_value),
                })

        return changes

    # --------------------------------------
    # COMPARACIÓN INTELIGENTE
    # --------------------------------------

    def _has_changed(self, old, new):
        """
        Detecta cambios reales evitando falsos positivos.
        """

        # Ambos None
        if old is None and new is None:
            return False

        # Normalización básica
        return self._normalize(old) != self._normalize(new)

    # --------------------------------------
    # NORMALIZACIÓN DE VALORES
    # --------------------------------------

    def _normalize(self, value):
        """
        Normaliza valores para comparación consistente.
        """

        # None
        if value is None:
            return None

        # Model instances (FK)
        if hasattr(value, "pk") and hasattr(value, "_meta"):
            return {
                "id": value.pk,
                "model": value._meta.label
            }

        # Querysets o listas
        if isinstance(value, (list, tuple)):
            return [self._normalize(v) for v in value]

        # Diccionarios (JSONField)
        if isinstance(value, dict):
            return {
                k: self._normalize(v)
                for k, v in value.items()
            }

        # Default
        return str(value)

    # --------------------------------------
    # HELPERS DE ALTO NIVEL
    # --------------------------------------

    def has_changes(self, old_data, new_data=None):
        """
        Booleano rápido: hubo cambios o no.
        """
        return len(self.diff(old_data, new_data)) > 0

    def changed_fields(self, old_data, new_data=None):
        """
        Lista de campos modificados.
        """
        return [c["field"] for c in self.diff(old_data, new_data)]