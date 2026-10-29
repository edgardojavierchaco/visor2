from django import forms
from django.core.exceptions import ValidationError
from .models import Alumnos_Bilingue, Nivel_curso
from .services.queries import schools

class RegistroForm(forms.ModelForm):
    class Meta:
        model=Alumnos_Bilingue
        fields=['cueanexo','nivel','curso','seccion','lengua','varones','mujeres']
    def __init__(self,*args,request=None,**kwargs):
        self.request=request
        super().__init__(*args,**kwargs)
        nivel=self.data.get('nivel') if self.is_bound else self.instance.nivel
        self.fields['curso'].queryset=Nivel_curso.objects.filter(nivel=nivel) if nivel else Nivel_curso.objects.none()
        if request:
            disponibles=list(schools(request).values_list('cueanexo','nom_est').distinct().order_by('cueanexo'))
            self.fields['cueanexo']=forms.ChoiceField(choices=[('','Seleccione un establecimiento')]+[(cue, f'{cue} — {name}') for cue,name in disponibles])
        for f in self.fields.values():
            f.widget.attrs['class']='form-control'
    def clean(self):
        data=super().clean()
        if data.get('curso') and data.get('nivel') and data['curso'].nivel!=data['nivel']:
            self.add_error('curso','El curso no corresponde al nivel seleccionado.')
        values=[data.get('varones'),data.get('mujeres')]
        if all(v is not None for v in values) and any(v<0 for v in values):
            raise ValidationError('Las cantidades no pueden ser negativas.')
        if all(data.get(k) for k in ('cueanexo','nivel','curso','seccion','lengua')):
            qs=Alumnos_Bilingue.objects.filter(**{k:data[k] for k in ('cueanexo','nivel','curso','seccion','lengua')})
            if self.instance.pk:
                qs=qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe esta combinación. Edite el registro existente.')
        return data
