from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password

from apps.usuarios.models import (
    UsuarioIntermedia,
    UsuariosVisualizador,
    NivelAcceso,
    Rol,
    PerfilUsuario
)



class Command(BaseCommand):

    help = "Importa usuarios Aplicadores desde tabla intermedia"


    def handle(self, *args, **kwargs):


        nivel = NivelAcceso.objects.get(
            tacceso="Aplicador"
        )


        rol = Rol.objects.get(
            nombre="Aplicador"
        )


        creados = 0
        existentes = 0


        for dato in UsuarioIntermedia.objects.all():


            existe = UsuariosVisualizador.objects.filter(
                username=dato.cuil
            ).exists()


            if existe:

                existentes += 1

                self.stdout.write(
                    f"Existe: {dato.cuil}"
                )

                continue



            usuario = UsuariosVisualizador.objects.create(

                username=dato.cuil,

                apellido=dato.apellido,

                nombres=dato.nombres,

                correo=dato.correo,

                telefono=dato.telefono,


                password=make_password(
                    dato.dni
                ),


                nivelacceso=nivel,


                activo=True,

                is_staff=True,

                is_superuser=False

            )


            PerfilUsuario.objects.create(
                usuario=usuario,
                rol=rol
            )


            creados += 1


            self.stdout.write(
                self.style.SUCCESS(
                    f"Creado: {dato.cuil}"
                )
            )


        self.stdout.write(
            self.style.SUCCESS(
                f"""
                Finalizado

                Creados: {creados}
                Existentes: {existentes}
                """
            )
        )