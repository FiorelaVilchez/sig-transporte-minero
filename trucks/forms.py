from django import forms
from .models import Vehiculo

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = [
            'placa', 'tipo', 'capacidad', 'estado', 
            'revision_tecnica_vigente', 'seguro_vigente', 
            'homologacion', 'mantenimiento_programado'
        ]
        widgets = {
            'mantenimiento_programado': forms.DateInput(attrs={'type': 'date'}),
        }
