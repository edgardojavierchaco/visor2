"""Ejecutar en el entorno aislado de pruebas/; nunca contra datos de producción."""
import uuid
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.consultasge.models_padron import CapaUnicaOfertas
from . import models as m
from .domain.access import get_user_cueanexos
from .domain.catalogs import expandir_rangos
from .services.crud import change_activity, archive_person, save_person, Conflict
from .forms import PersonaForm


def valid_cuil(number):
    base = '20' + str(number).zfill(8)
    digit = 11 - sum(int(n)*w for n,w in zip(base,[5,4,3,2,7,6,5,4,3,2])) % 11
    digit = 0 if digit == 11 else 9 if digit == 10 else digit
    return base + str(digit)


class MinisterialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.director = User.objects.create_user(username='20123456786', nivelacceso='Director/a')
        cls.other = User.objects.create_user(username='20999999990', nivelacceso='Director/a')
        cls.regional = User.objects.create_user(username='regional', nivelacceso='Regional')
        cls.empty_regional = User.objects.create_user(username='sinregion', nivelacceso='Regional')
        cls.admin = User.objects.create_user(username='admin', is_superuser=True)
        CapaUnicaOfertas.objects.create(cueanexo=220000100, nom_est='Escuela Uno', resploc_cuitcuil='20-12345678-6', region_loc='R1')
        CapaUnicaOfertas.objects.create(cueanexo=220000200, nom_est='Escuela Dos', resploc_cuitcuil='20999999990', region_loc='R2', sector='Privado')
        CapaUnicaOfertas.objects.create(cueanexo=220000300, nom_est='Escuela Privada R1', resploc_cuitcuil='20999999990', region_loc='R1', sector='Privado')
        m.AccesoRegional.objects.create(usuario=cls.regional, region='R1')
        m.Provincias.objects.create(c_provincia=22, descrip_provincia='Chaco')
        m.Provincias.objects.create(c_provincia=10, descrip_provincia='Otra')
        m.Localidades.objects.create(c_localidad=1, descrip_localidad='Resistencia', c_departamento=1, descrip_departamento='San Fernando', c_provincia_id=22)
        m.Localidades.objects.create(c_localidad=2, descrip_localidad='Otra', c_departamento=2, descrip_departamento='Otro', c_provincia_id=10)
        m.Sexo.objects.create(c_sexo=1, descrip_sexo='X')
        m.Modalidades.objects.create(c_modalidad=1, descrip_modalidad='Común')
        m.NivelServicio.objects.create(c_nivel=1, descrip_nivel='Primario')
        m.ModalidadNivel.objects.create(modalidad_id=1, nivel_id=1)
        m.NomencladorCeic.objects.create(c_ceic=1, descripcion='Cargo', estado='Activo', c_niv=1, t_nivel='Nivel')
        m.NomencladorCeic.objects.create(c_ceic=2, descripcion='Otro cargo', estado='Activo', c_niv=1, t_nivel='Nivel')
        m.ModalidadNivelCeic.objects.create(modalidad_id=1, nivel_id=1, rango_ceic='1')
        m.SituacionServicio.objects.create(cod_sitrev=1, descrip_sitrev='Titular')
        m.CondicionActividad.objects.create(cod_condicion=1, descrip_condicion='En actividad')
        m.TipoDesigFunc.objects.create(c_desigfunc=1, desigfunc_descripcion='Cargo')
        m.TipoFunciones.objects.create(c_funciones=1, funciones_descripcion='Servicio')
        m.Grado_anio.objects.create(c_grado_anio=1, nombre_grado_anio='Primero', c_niv_grado=1, t_niv_grado='Nivel')
        m.Secciones.objects.create(c_seccion=1, nombre_seccion='A', c_niv_seccion=1, t_niv_seccion='Nivel')
        m.TitulosEspacios.objects.create(cod_titulo=1, descrip_titulo='Matemática')
        cls.person = m.Personas.objects.create(cuil=valid_cuil(12345678), dni='12345678', apellido='PEREZ', nombre='ANA', f_nacimiento=date(1980,1,1), sexo_id=1, provincia_id=22, localidad_id=1)
        cls.foreign = m.Personas.objects.create(cuil=valid_cuil(23456789), dni='23456789', apellido='LOPEZ', nombre='JUAN', f_nacimiento=date(1980,1,1), sexo_id=1, provincia_id=22, localidad_id=1)
        cls.activity = cls.make_activity(cls.person, '220000100')
        cls.foreign_activity = cls.make_activity(cls.foreign, '220000200')

    @staticmethod
    def make_activity(person, cue):
        return m.RegistroActividades.objects.create(persona=person, cueanexo=cue, categoria='NO DOCENTE', modalidad_id=1, niveles_id=1, sit_revista_id=1, cond_actividad_id=1, t_designacion_id=1, ceic_id=1, f_desde=date(2020,1,1), carga_horaria=Decimal('20'), estado='ACTIVO', funciones_id=1, f_desde_funciones=date(2020,1,1))

    def setUp(self):
        self.client.force_login(self.director)

    def url(self, name, *args):
        return reverse('bnhpersonas:'+name, args=args)

    def activity_data(self, **changes):
        data = dict(operation_id=str(uuid.uuid4()), cueanexo='220000100', categoria='NO DOCENTE', modalidad='1', niveles='1', sit_revista='1', cond_actividad='1', designacion='CARGO', t_designacion='1', ceic='1', grado_anio='', turno='MAÑANA', secciones='', espacios='', f_desde='2020-01-01', f_hasta='', carga_horaria='20', estado='ACTIVO', funciones='1', f_desde_funciones='2020-01-01', f_hasta_funciones='', version='1')
        data.update(changes)
        return data

    def person_data(self, **changes):
        data = dict(cuil=valid_cuil(34567890), dni='34567890', apellido='GOMEZ', nombre='MARIA', f_nacimiento='1980-01-01', sexo='1', provincia='22', localidad='1', codigo_area='', telefono='')
        data.update(changes)
        return data

    def test_director_scope(self):
        self.assertEqual(set(get_user_cueanexos(self.director)), {'220000100'})

    def test_regional_private_and_state(self):
        self.assertEqual(set(get_user_cueanexos(self.regional)), {'220000100','220000300'})
        self.assertFalse(get_user_cueanexos(self.empty_regional).exists())
        self.client.force_login(self.empty_regional)
        self.assertEqual(self.client.get(self.url('personas_list')).status_code, 403)

    def test_anonymous_mutations_denied(self):
        self.client.logout()
        for url in [self.url('carga_personal'), self.url('guardar_persona_ajax'), self.url('editar_actividad', self.activity.pk), self.url('horario_agregar', self.activity.pk), self.url('eliminar_horario', 1)]:
            self.assertEqual(self.client.post(url, {}).status_code, 302)

    def test_object_access_and_search(self):
        for name, pk in [('personas_detail', self.foreign.pk), ('carga_personal_edit', self.foreign.pk), ('editar_actividad', self.foreign_activity.pk)]:
            self.assertEqual(self.client.get(self.url(name, pk)).status_code, 404)
        response = self.client.get(self.url('buscar_persona'), {'cuil':self.foreign.cuil})
        self.assertFalse(response.json()['existe'])

    def test_views_render(self):
        for name, args in [('personas_list', []), ('personas_detail', [self.person.pk]), ('carga_personal', []), ('carga_personal_edit', [self.person.pk]), ('editar_actividad', [self.activity.pk]), ('vincular_persona', [])]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.url(name,*args)).status_code,200)

    def test_atomic_creation_non_teaching(self):
        data = {'persona-'+k:v for k,v in self.person_data().items()}
        data.update({'actividad-'+k:v for k,v in self.activity_data().items()})
        response = self.client.post(self.url('carga_personal'), data)
        self.assertEqual(response.status_code,302, response.content[:2000])
        person = m.Personas.objects.get(dni='34567890')
        obj = person.actividades.get()
        self.assertIsNone(obj.grado_anio_id)
        self.assertIsNone(obj.f_hasta)
        self.assertTrue(m.EventoAuditoria.objects.filter(entidad='personas', objeto_id=person.pk).exists())

    def test_invalid_activity_creates_no_orphan(self):
        data = {'persona-'+k:v for k,v in self.person_data().items()}
        data.update({'actividad-'+k:v for k,v in self.activity_data(cueanexo='220000200').items()})
        self.assertEqual(self.client.post(self.url('carga_personal'), data).status_code,200)
        self.assertFalse(m.Personas.objects.filter(dni='34567890').exists())

    def test_teacher_creation(self):
        data = self.activity_data(categoria='DOCENTE', grado_anio='1', secciones='1', espacios='Matemática')
        response = self.client.post(self.url('nueva_actividad',self.person.pk),data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.person.actividades.filter(categoria='DOCENTE').count(),1)

    def test_stale_version_rejected(self):
        m.RegistroActividades.objects.filter(pk=self.activity.pk).update(version=2)
        response = self.client.post(self.url('editar_actividad', self.activity.pk), self.activity_data(carga_horaria='30'))
        self.assertContains(response, 'Otro usuario modificó')
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.carga_horaria, Decimal('20'))

    def test_person_edit_resets_all_validations(self):
        shared = self.make_activity(self.person, '220000200')
        m.RegistroActividades.objects.filter(persona=self.person).update(validacion='VALIDADO')
        form = PersonaForm(self.person_data(cuil=self.person.cuil,dni=self.person.dni, version=1),instance=self.person)
        self.assertTrue(form.is_valid(),form.errors)
        save_person(self.director, form)
        shared.refresh_from_db()
        self.assertEqual(shared.validacion,'BORRADOR')
        self.assertEqual(shared.version,2)

    def test_delete_restore_preserves_other_school(self):
        other = self.make_activity(self.person, '220000200')
        change_activity(self.director,self.activity.pk,'ELIMINAR',1,'Carga duplicada')
        other.refresh_from_db()
        self.assertFalse(other.eliminado)
        with self.assertRaises(ValidationError):
            archive_person(self.director,self.person.pk,1,'Archivar prueba')
        change_activity(self.director,self.activity.pk,'RESTAURAR',2,'Restaurar prueba')
        self.activity.refresh_from_db()
        self.assertFalse(self.activity.eliminado)
        self.assertEqual(self.activity.version,3)

    def test_archive_after_last_deleted(self):
        change_activity(self.director,self.activity.pk,'ELIMINAR',1,'Carga incorrecta')
        response = self.client.post(self.url('eliminar_persona',self.person.pk), {'version':1,'motivo':'Registro incorrecto'})
        self.assertEqual(response.status_code,302)
        self.person.refresh_from_db()
        self.assertTrue(self.person.archivada)
        self.assertTrue(m.RegistroActividades.objects.filter(pk=self.activity.pk).exists())

    def test_schedules_get_no_write_and_overlap(self):
        self.assertEqual(self.client.get(self.url('horario_agregar',self.activity.pk)).status_code,405)
        self.assertFalse(m.ActividadSede.objects.exists())
        self.client.get(self.url('editar_actividad',self.activity.pk))
        self.assertFalse(m.ActividadSede.objects.exists())
        payload = dict(dia='LUNES',hora_desde='08:00',hora_hasta='10:00',version=1)
        self.assertEqual(self.client.post(self.url('horario_agregar',self.activity.pk),payload).status_code,302)
        schedule = m.HorarioActividad.objects.get()
        self.assertEqual(self.client.get(self.url('eliminar_horario',schedule.pk)).status_code,405)
        payload.update(hora_desde='09:00',hora_hasta='11:00',version=2)
        self.assertEqual(self.client.post(self.url('horario_agregar',self.activity.pk),payload).status_code,400)
        self.assertEqual(m.HorarioActividad.objects.count(),1)

    def test_schedule_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.director)
        response = client.post(self.url('horario_agregar',self.activity.pk), dict(dia='LUNES',hora_desde='08:00',hora_hasta='09:00',version=1))
        self.assertEqual(response.status_code,403)

    def test_non_authorized_catalog_forgery(self):
        response = self.client.post(self.url('editar_actividad',self.activity.pk),self.activity_data(ceic='2'))
        self.assertEqual(response.status_code,200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.ceic_id,1)

    def test_province_change_and_seven_digit_dni(self):
        data=self.person_data(cuil=valid_cuil(1234567),dni='1234567',provincia='10',localidad='2')
        form=PersonaForm(data)
        self.assertTrue(form.is_valid(),form.errors)
        form=PersonaForm(self.person_data(provincia='10',localidad='1'))
        self.assertFalse(form.is_valid())

    def test_unique_cuil_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            # bulk_create omite clean, pero no puede evadir la restricción de BD.
            m.Personas.objects.bulk_create([m.Personas(cuil=self.person.cuil,dni=self.person.dni,apellido='X',nombre='Y',f_nacimiento=date(1980,1,1),sexo_id=1,provincia_id=22,localidad_id=1)])

    def test_link_existing_without_editing_identity(self):
        data=dict(cuil=self.foreign.cuil,dni=self.foreign.dni,apellido=self.foreign.apellido,confirmo='on')
        data.update({'actividad-'+k:v for k,v in self.activity_data().items()})
        response=self.client.post(self.url('vincular_persona'),data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.foreign.actividades.count(),2)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.version,1)

    def test_validate_and_observe_permissions(self):
        change_activity(self.director,self.activity.pk,'VALIDAR',1,'Datos verificados')
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            change_activity(self.director,self.activity.pk,'OBSERVAR',2,'Revisar datos')
        change_activity(self.regional,self.activity.pk,'OBSERVAR',2,'Revisar datos')
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.validacion,'OBSERVADO')

    def test_export_scoped_and_filters(self):
        response=self.client.get(self.url('exportar_personal'))
        text=b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('PEREZ',text)
        self.assertNotIn('LOPEZ',text)
        response=self.client.get(self.url('personas_list'),{'q':'LOPEZ'})
        self.assertNotContains(response,'Ver ficha')

    def test_malformed_catalog_parameter(self):
        self.assertEqual(self.client.get(self.url('filtrar_datos_actividad'),{'modalidad':'abc'}).status_code,400)
        with self.assertRaises(ValidationError):
            expandir_rangos('1-999999999')


    def test_replayed_activity_post_does_not_duplicate(self):
        data = self.activity_data()
        url = self.url('nueva_actividad',self.person.pk)
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(self.client.post(url,data).status_code,200)
        self.assertEqual(self.person.actividades.count(),2)

    def test_archived_person_restore_audited(self):
        from .services.crud import restore_person
        change_activity(self.director,self.activity.pk,'ELIMINAR',1,'Carga incorrecta')
        archive_person(self.director,self.person.pk,1,'Registro incorrecto')
        restored = restore_person(self.admin,self.person.pk,2,'Restitución autorizada')
        self.assertFalse(restored.archivada)
        self.assertTrue(m.EventoAuditoria.objects.filter(accion='RESTAURAR_PERSONA',objeto_id=restored.pk).exists())

    def test_preflight_readonly_finds_invalid_data(self):
        from .domain.preflight import inspect_data
        m.Personas.objects.filter(pk=self.person.pk).update(cuil='123')
        issues=inspect_data(m.Personas,m.RegistroActividades,m.HorarioActividad)
        self.assertIn(self.person.pk, issues['personas_cuil_no_canonico_ids'])
        self.person.refresh_from_db()
        self.assertEqual(self.person.cuil,'123')
