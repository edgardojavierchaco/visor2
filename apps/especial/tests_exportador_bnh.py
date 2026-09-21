# -*- coding: utf-8 -*-

from django.test import SimpleTestCase

from .validators.bnh_validators import (
    validar_combinaciones_especiales,
    validar_documento,
)


class ExportadorBNHValidadoresTests(SimpleTestCase):
    def test_dni_de_siete_digitos_se_completa_con_cero(self):
        self.assertEqual(validar_documento(1, "1234567"), "01234567")

    def test_no_posee_documento_exporta_vacío(self):
        self.assertEqual(validar_documento(11, ""), "")

    def test_documento_extranjero_alfanumerico(self):
        self.assertEqual(validar_documento(13, "ab123"), "AB123")

    def test_rechaza_dos_niveles_de_especial(self):
        with self.assertRaises(ValueError):
            validar_combinaciones_especiales(
                1,
                [
                    {"oferta": "Especial - Inicial"},
                    {"oferta": "Especial - Primaria"},
                ],
            )
