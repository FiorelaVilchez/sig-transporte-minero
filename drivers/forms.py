from django import forms
from .models import Conductor

class ConductorForm(forms.ModelForm):
    class Meta:
        model = Conductor
        fields = [
            'nombres', 'apellidos', 'dni', 'licencia', 
            'especialidad', 'estado', 'telefono', 
            'fecha_nacimiento', 'fecha_ingreso'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
        }
