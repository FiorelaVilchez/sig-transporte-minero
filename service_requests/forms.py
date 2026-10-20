from django import forms

from trucks.models import TipoVehiculo

from .models import SolicitudServicio
from .services import CAMPOS_DE_PROGRAMACION


class SolicitudServicioForm(forms.ModelForm):
    motivo_cambio = forms.CharField(
        required=False, max_length=255, label="Motivo del cambio",
        widget=forms.TextInput(attrs={'placeholder': 'Ej. El cliente adelantó la hora de salida'}),
    )

    class Meta:
        model = SolicitudServicio
        fields = [
            'cliente', 'fecha_servicio', 'hora_servicio',
            'origen', 'destino', 'tipo_servicio',
            'prioridad', 'tipo_vehiculo_requerido', 'pasajeros', 'duracion_horas', 'km_estimados',
            'estado_solicitud',
        ]
        widgets = {
            'fecha_servicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'hora_servicio': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TipoVehiculo.objects.filter(activo=True)
        if self.instance.pk and self.instance.tipo_vehiculo_requerido_id:
            qs = (qs | TipoVehiculo.objects.filter(nombre=self.instance.tipo_vehiculo_requerido_id)).distinct()
        self.fields['tipo_vehiculo_requerido'].queryset = qs
        self.fields['tipo_vehiculo_requerido'].empty_label = "Seleccione un tipo"
        self.fields['tipo_vehiculo_requerido'].label_from_instance = (
            lambda t: f"{t.nombre} (hasta {t.asientos_referencia} pasajeros)"
        )
        self.es_edicion = bool(self.instance.pk)

    def clean(self):
        datos = super().clean()
        if self.es_edicion and self.has_changed():
            cambios_programacion = [c for c in self.changed_data if c in CAMPOS_DE_PROGRAMACION]
            if cambios_programacion and not (datos.get('motivo_cambio') or '').strip():
                self.add_error('motivo_cambio', "Indique el motivo: el cambio queda registrado en la bitácora.")
        return datos
