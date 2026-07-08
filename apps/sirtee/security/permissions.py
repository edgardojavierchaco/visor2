from apps.usuarios.models import PerfilUsuario


class SirteePermissions:

    def __init__(self, user):
        self.user = user
        self.perfil = getattr(user, "perfil", None)

    # --------------------------------------
    # CATEGORÍA BASE DEL ROL
    # --------------------------------------

    def categoria(self):
        if not self.perfil or not self.perfil.rol:
            return "propio"
        return self.perfil.rol.categoria_acceso

    # --------------------------------------
    # NIVEL DE ACCESO LÓGICO
    # --------------------------------------

    def is_global(self):
        return self.categoria() == "all"

    def is_regional(self):
        return self.categoria() == "regional"

    def is_propio(self):
        return self.categoria() == "propio"

    def is_nivel(self):
        return self.categoria() == "nivel"

    def is_supervisor(self):
        return self.categoria() == "supervisor"

    # --------------------------------------
    # PERMISOS POR MÓDULO SIRTEE
    # --------------------------------------

    def can_view_dashboard(self):
        return self.categoria() in ["all", "regional", "nivel", "supervisor"]

    def can_manage_relevamientos(self):
        return self.categoria() in ["all", "regional", "nivel"]

    def can_manage_hallazgos(self):
        return self.categoria() in ["all", "regional", "supervisor"]

    def can_manage_intervenciones(self):
        return self.categoria() in ["all", "regional"]

    # --------------------------------------
    # FILTRO TERRITORIAL REAL (CRÍTICO)
    # --------------------------------------

    def filter_relevamientos(self, qs):
        """
        Filtra según cueanexos del usuario o región.
        """

        if self.is_global():
            return qs

        if self.is_regional():
            # usa SQL existente del usuario
            cueanexos = self.user.obtener_cueanexos()
            cueanexo_ids = [c[0] for c in cueanexos if c]

            return qs.filter(escuela__cueanexo__in=cueanexo_ids)

        if self.is_propio():
            cueanexos = self.user.cueanexos.values_list("cueanexo", flat=True)
            return qs.filter(escuela__cueanexo__in=cueanexos)

        if self.is_nivel():
            cueanexos = self.user.obtener_cueanexos()
            cueanexo_ids = [c[0] for c in cueanexos if c]
            return qs.filter(escuela__cueanexo__in=cueanexo_ids)

        return qs.none()

    def filter_hallazgos(self, qs):
        return self.filter_relevamientos(qs)

    def filter_intervenciones(self, qs):
        return self.filter_relevamientos(qs)