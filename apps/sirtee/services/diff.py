from datetime import datetime


class DiffService:
    """
    Servicio de generación de diffs legibles.

    Convierte cambios técnicos en información entendible
    para UI, logs y reportes.
    """

    # --------------------------------------
    # DIFF PRINCIPAL
    # --------------------------------------

    def build_diff(self, changes):
        """
        Recibe lista de cambios del tracker y los transforma
        en estructura legible.
        """

        if not changes:
            return {
                "has_changes": False,
                "summary": "Sin cambios detectados",
                "changes": []
            }

        formatted_changes = [
            self._format_change(c) for c in changes
        ]

        return {
            "has_changes": True,
            "summary": self._build_summary(changes),
            "changes": formatted_changes,
            "total_changes": len(changes)
        }

    # --------------------------------------
    # FORMATEO DE CAMBIO INDIVIDUAL
    # --------------------------------------

    def _format_change(self, change):
        """
        Normaliza cada cambio en formato UI-friendly.
        """

        return {
            "field": change.get("field"),
            "before": self._normalize_value(change.get("old")),
            "after": self._normalize_value(change.get("new")),
            "type": self._detect_change_type(change)
        }

    # --------------------------------------
    # RESUMEN INTELIGENTE
    # --------------------------------------

    def _build_summary(self, changes):
        """
        Genera resumen humano del cambio.
        """

        fields = [c["field"] for c in changes]

        if len(fields) == 1:
            return f"Se modificó el campo '{fields[0]}'"

        if len(fields) <= 3:
            return f"Se modificaron los campos: {', '.join(fields)}"

        return f"Se modificaron {len(fields)} campos"

    # --------------------------------------
    # TIPO DE CAMBIO
    # --------------------------------------

    def _detect_change_type(self, change):
        """
        Clasifica el tipo de cambio.
        """

        old = change.get("old")
        new = change.get("new")

        if old is None and new is not None:
            return "CREATE_VALUE"

        if old is not None and new is None:
            return "DELETE_VALUE"

        return "UPDATE_VALUE"

    # --------------------------------------
    # NORMALIZACIÓN PARA UI
    # --------------------------------------

    def _normalize_value(self, value):
        """
        Convierte valores técnicos en strings legibles.
        """

        if value is None:
            return "—"

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(value, bool):
            return "Sí" if value else "No"

        return str(value)

    # --------------------------------------
    # DIFF AGRUPADO POR ENTIDAD
    # --------------------------------------

    def group_by_entity(self, entity_name, diff_data):
        """
        Agrupa diff para una entidad específica.
        """

        return {
            "entity": entity_name,
            "timestamp": datetime.now(),
            "diff": diff_data,
        }

    # --------------------------------------
    # DIF RESUMIDO (PARA LISTADOS)
    # --------------------------------------

    def compact_diff(self, changes):
        """
        Versión corta para tablas/listados.
        """

        if not changes:
            return "Sin cambios"

        fields = [c["field"] for c in changes]

        if len(fields) == 1:
            return f"{fields[0]} modificado"

        return f"{len(fields)} campos modificados"