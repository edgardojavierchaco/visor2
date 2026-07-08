from apps.sirtee.models.empresas import Empresa, Contrato


class EmpresaService:

    @staticmethod
    def crear_empresa(data):
        return Empresa.objects.create(
            nombre=data["nombre"],
            cuit=data["cuit"],
            contacto=data.get("contacto"),
            telefono=data.get("telefono"),
            email=data.get("email"),
        )

    @staticmethod
    def activar_empresa(empresa):
        empresa.activo = True
        empresa.save()
        return empresa

    @staticmethod
    def desactivar_empresa(empresa):
        empresa.activo = False
        empresa.save()
        return empresa

    @staticmethod
    def crear_contrato(empresa, data):
        return Contrato.objects.create(
            empresa=empresa,
            descripcion=data["descripcion"],
            fecha_inicio=data["fecha_inicio"],
            fecha_fin=data.get("fecha_fin"),
            monto=data["monto"],
        )