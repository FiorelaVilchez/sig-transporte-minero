from django import forms
from .models import SolicitudServicio

class SolicitudServicioForm(forms.ModelForm):
    class Meta:
        model = SolicitudServicio
        fields = [
            'cliente', 'fecha_servicio', 'hora_servicio', 
            'origen', 'destino', 'tipo_servicio', 
            'prioridad', 'tipo_vehiculo_requerido', 'estado_solicitud'
        ]
        widgets = {
            'fecha_servicio': forms.DateInput(attrs={'type': 'date'}),
            'hora_servicio': forms.TimeInput(attrs={'type': 'time'}),
        }
