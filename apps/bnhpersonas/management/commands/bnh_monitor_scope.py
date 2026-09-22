from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.bnhpersonas.monitoring.access import resolve_scope


class Command(BaseCommand):
    help = "Muestra el alcance efectivo de Seguimiento BNH para un usuario."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario inexistente: {username}") from exc

        scope = resolve_scope(user)

        self.stdout.write(f"Usuario: {user}")
        self.stdout.write(f"Rol: {scope.role or '(sin rol)'}")
        self.stdout.write(f"Tipo de alcance: {scope.kind}")
        self.stdout.write(f"Alcance: {scope.label}")

        if scope.cueanexos:
            self.stdout.write("CUEANEXO:")
            for cue in scope.cueanexos:
                self.stdout.write(f"  - {cue}")

        if scope.regiones:
            self.stdout.write("Regionales:")
            for region in scope.regiones:
                self.stdout.write(f"  - {region}")
