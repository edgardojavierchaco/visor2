import uuid 
from django.conf import settings
from django.db import models
from django.db.models import Count
from apps.usuarios.models import UsuariosVisualizador

User = settings.AUTH_USER_MODEL

class ModelBase(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, db_index=True, editable=False)
    tiempo = models.DateTimeField(auto_now_add=True)
    actualizar = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class CanalMensaje(ModelBase):
    canal = models.ForeignKey('Canal', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()

    class Meta:
        app_label = 'Dm'

class CanalUsuario(ModelBase):
    canal = models.ForeignKey('Canal', on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    es_gestor = models.BooleanField(default=False)

class CanalQuerySet(models.QuerySet):
    def solo_uno(self):
        return self.annotate(num_usuarios=Count('usuario')).filter(num_usuarios=1)

    def solo_dos(self):
        return self.annotate(num_usuarios=Count('usuario')).filter(num_usuarios=2)

    def filtrar_por_username(self, username):
        return self.filter(canalusuario__usuario__username=username)

class CanalManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        return CanalQuerySet(self.model, using=self._db)

    def filtrar_ms_por_privado(self, username_a, username_b):
        return self.get_queryset().solo_dos().filtrar_por_username(username_a).filtrar_por_username(username_b)

    def obtener_o_crear_canal_usuario_actual(self, user):
        qs = self.get_queryset().solo_uno().filtrar_por_username(user.username)
        if qs.exists():
            return qs.order_by("tiempo").first(), False

        canal_obj = Canal.objects.create()
        CanalUsuario.objects.create(usuario=user, canal=canal_obj)
        return canal_obj, True

    def obtener_o_crear_canal_ms(self, username_a, username_b):
        qs = self.filtrar_ms_por_privado(username_a, username_b)
        if qs.exists():
            return qs.order_by("tiempo").first(), False

        User = UsuariosVisualizador
        usuario_a, usuario_b = None, None

        try:
            usuario_a = User.objects.get(username=username_a)
            usuario_b = User.objects.get(username=username_b)
        except User.DoesNotExist:
            return None, False

        obj_canal = Canal.objects.create()
        canal_usuario_a = CanalUsuario(usuario=usuario_a, canal=obj_canal)
        canal_usuario_b = CanalUsuario(usuario=usuario_b, canal=obj_canal)
        CanalUsuario.objects.bulk_create([canal_usuario_a, canal_usuario_b])
        return obj_canal, True

    def obtener_o_crear_canal_usuario(self, user, canal_nombre):
        usuario_canal = CanalUsuario.objects.filter(usuario=user).first()
        if usuario_canal:
            return usuario_canal.canal, False

        canal = Canal.objects.filter(nombre=canal_nombre).first()
        if canal:
            CanalUsuario.objects.create(usuario=user, canal=canal)
            return canal, True
        return None, False

class Canal(ModelBase):
    NOMBRE_CANAL_CHOICES = [
        ('SIE', 'SIE'),
        ('RelevamientoAnual', 'Relevamiento Anual'),
    ]

    nombre = models.CharField(max_length=50, choices=NOMBRE_CANAL_CHOICES, unique=True)
    usuario = models.ManyToManyField(User, blank=True, through=CanalUsuario)

    objects = CanalManager()

    def __str__(self):
        return self.nombre

from django import forms

class FormMensajes(forms.Form):
    mensaje = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'formulario_ms',
        'placeholder': 'Escribe tu mensaje'
    }))

class CanalEleccionForm(forms.Form):
    CANALES = [
        ('SIE', 'SIE'),
        ('RelevamientoAnual', 'Relevamiento Anual'),
    ]
    
    canal = forms.ChoiceField(choices=CANALES, label="Selecciona un canal", widget=forms.RadioSelect)
