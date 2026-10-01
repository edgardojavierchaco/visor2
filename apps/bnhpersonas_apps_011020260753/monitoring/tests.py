from types import SimpleNamespace
from django.test import SimpleTestCase, override_settings

from .roles import normalize_role, role_kind


class RoleNormalizationTests(SimpleTestCase):
    def user(self, role, superuser=False):
        return SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=superuser,
            nivelacceso=role,
        )

    def test_normalize_role(self):
        self.assertEqual(normalize_role("  Subsecretaría  "), "subsecretaria")

    def test_global_roles(self):
        for role in (
            "Administrador",
            "Gestor",
            "Director General",
            "Directora General",
            "Subsecretario",
            "Subsecretaria",
            "Ministro",
            "Ministra",
        ):
            self.assertEqual(role_kind(self.user(role)), "global")

    def test_supervisor(self):
        self.assertEqual(role_kind(self.user("Supervisor")), "supervisor")

    def test_regional(self):
        self.assertEqual(role_kind(self.user("Regional")), "regional")

    def test_director_not_authorized_by_default(self):
        self.assertEqual(role_kind(self.user("Director")), "none")
