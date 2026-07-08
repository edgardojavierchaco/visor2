from django.db import models


class Documento(models.Model):

    TIPOS = [
        ("ACTA", "Acta"),
        ("INFORME", "Informe"),
        ("FOTO", "Foto"),
        ("PLANO", "Plano"),
        ("CONTRATO", "Contrato"),
        ("OTRO", "Otro"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS)

    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to="sirtee/documentos/")

    # relaciones opcionales (polimórfico simple)
    relevamiento = models.ForeignKey(
        "sirtee.Relevamiento",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    hallazgo = models.ForeignKey(
        "sirtee.Hallazgo",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    intervencion = models.ForeignKey(
        "sirtee.Intervencion",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo