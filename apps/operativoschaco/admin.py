from django.contrib import admin
from .models import AlumnosSecundaria, Opcion, Pregunta, ExamenAlumnoCueanexoL, Respuesta, Categoria, PreguntaM, ExamenAlumnoCueanexoM, RespuestaM

# Registro de los modelos en el admin
@admin.register(AlumnosSecundaria)
class AlumnosSecundariaAdmin(admin.ModelAdmin):
    list_display = ('dni', 'apellidos', 'nombres', 'cueanexo')
    search_fields = ('dni', 'apellidos', 'nombres')


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'puntaje_maximo', 'mostrar_categorias')
    search_fields = ('descripcion',)
    list_filter = ('categorias',)  # Asegúrate de que "categorias" sea un campo ManyToMany en el modelo Pregunta

    # Método para mostrar si tiene categorías
    def mostrar_categorias(self, obj):
        return ", ".join([cat.nombre for cat in obj.categorias.all()]) if obj.categorias.exists() else "Sin categorías"
    mostrar_categorias.short_description = 'Categorías'


@admin.register(ExamenAlumnoCueanexoL)
class ExamenAlumnoCueanexoLAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'fecha_examen')
    list_filter = ('fecha_examen',)
    search_fields = ('alumno__dni', 'alumno__apellidos', 'alumno__nombres')


@admin.register(Respuesta)
class RespuestaAdmin(admin.ModelAdmin):
    list_display = ('examen', 'mostrar_pregunta', 'mostrar_opcion', 'mostrar_categoria', 'calcular_puntaje')
    search_fields = ('examen__alumno__dni', 'pregunta__descripcion')

    # Métodos personalizados
    def mostrar_pregunta(self, obj):
        return obj.pregunta.descripcion
    mostrar_pregunta.short_description = 'Pregunta'

    def mostrar_opcion(self, obj):
        return ", ".join([str(opcion['descripcion']) for opcion in obj.opciones_seleccionadas])
    mostrar_opcion.short_description = 'Opción Seleccionada'

    def mostrar_categoria(self, obj):
        return ", ".join(
            [str(opcion['categoria']) for opcion in obj.opciones_seleccionadas if opcion.get('categoria')]
        ) if obj.opciones_seleccionadas else "Sin categoría"
    mostrar_categoria.short_description = 'Categoría'

    def calcular_puntaje(self, obj):
        # Calcula el puntaje sumando los valores en opciones_seleccionadas
        return sum([opcion['puntaje'] for opcion in obj.opciones_seleccionadas])
    calcular_puntaje.short_description = 'Puntaje'


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)  # Agregar la coma convierte a tupla
    search_fields = ('nombre',)  # Agregar la coma convierte a tupla

@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'puntaje', 'categoria')  # Lista completa
    search_fields = ('descripcion',)  # Agregar la coma convierte a tupla


@admin.register(PreguntaM)
class PreguntaMAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'puntaje_maximo', 'mostrar_categorias')
    search_fields = ('descripcion',)
    list_filter = ('categorias',)  # Asegúrate de que "categorias" sea un campo ManyToMany en el modelo Pregunta

    # Método para mostrar si tiene categorías
    def mostrar_categorias(self, obj):
        return ", ".join([cat.nombre for cat in obj.categorias.all()]) if obj.categorias.exists() else "Sin categorías"
    mostrar_categorias.short_description = 'Categorías'


@admin.register(ExamenAlumnoCueanexoM)
class ExamenAlumnoCueanexoMAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'fecha_examen')
    list_filter = ('fecha_examen',)
    search_fields = ('alumno__dni', 'alumno__apellidos', 'alumno__nombres')


@admin.register(RespuestaM)
class RespuestaMAdmin(admin.ModelAdmin):
    list_display = ('examen', 'mostrar_pregunta', 'mostrar_opcion', 'mostrar_categoria', 'calcular_puntaje')
    search_fields = ('examen__alumno__dni', 'pregunta__descripcion')

    # Métodos personalizados
    def mostrar_pregunta(self, obj):
        return obj.pregunta.descripcion
    mostrar_pregunta.short_description = 'Pregunta'

    def mostrar_opcion(self, obj):
        return ", ".join([str(opcion['descripcion']) for opcion in obj.opciones_seleccionadas])
    mostrar_opcion.short_description = 'Opción Seleccionada'

    def mostrar_categoria(self, obj):
        return ", ".join(
            [str(opcion['categoria']) for opcion in obj.opciones_seleccionadas if opcion.get('categoria')]
        ) if obj.opciones_seleccionadas else "Sin categoría"
    mostrar_categoria.short_description = 'Categoría'

    def calcular_puntaje(self, obj):
        # Calcula el puntaje sumando los valores en opciones_seleccionadas
        return sum([opcion['puntaje'] for opcion in obj.opciones_seleccionadas])
    calcular_puntaje.short_description = 'Puntaje'