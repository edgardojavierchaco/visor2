"""Pruebas unitarias livianas de reglas críticas BNH.

Las pruebas de concurrencia real contra PostgreSQL se documentan en
``README_CONCURRENCIA_BNH_20260919.md`` porque requieren una base de prueba con
los catálogos ministeriales disponibles.
"""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .models import validar_cuil, validar_dni
from .services.crud import DUPLICATE_ACTIVITY_FIELDS, IDENTITY_FIELDS


class ValidationRulesTests(SimpleTestCase):
    def test_dni(self):
        validar_dni("12345678")
        validar_dni("1234567")
        with self.assertRaises(ValidationError):
            validar_dni("123")
        with self.assertRaises(ValidationError):
            validar_dni("12A45678")

    def test_cuil_rejects_wrong_length(self):
        with self.assertRaises(ValidationError):
            validar_cuil("123")


class ConcurrencyContractTests(SimpleTestCase):
    def test_possible_duplicate_key_is_business_definition(self):
        self.assertEqual(
            DUPLICATE_ACTIVITY_FIELDS,
            (
                "persona_id",
                "cueanexo",
                "tipo_personal_id",
                "ceic_id",
                "sit_revista_id",
                "t_designacion_id",
                "f_desde",
            ),
        )

    def test_identity_fields_are_explicit(self):
        self.assertEqual(
            IDENTITY_FIELDS,
            ("cuil", "dni", "apellido", "nombre", "f_nacimiento", "sexo_id"),
        )
