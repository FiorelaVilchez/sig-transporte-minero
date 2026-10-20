from django import forms

from .models import TipoVehiculo, Vehiculo


class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = [
            'placa', 'tipo', 'capacidad', 'estado',
            'revision_tecnica_vigente', 'seguro_vigente',
            'homologacion', 'mantenimiento_programado'
        ]
        widgets = {
            'mantenimiento_programado': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TipoVehiculo.objects.filter(activo=True)
        if self.instance.pk and self.instance.tipo_id:
            qs = (qs | TipoVehiculo.objects.filter(nombre=self.instance.tipo_id)).distinct()
        self.fields['tipo'].queryset = qs
        self.fields['tipo'].empty_label = "Seleccione un tipo"
        self.fields['tipo'].label_from_instance = lambda t: f"{t.nombre} (referencia {t.asientos_referencia} asientos)"


class TipoVehiculoForm(forms.ModelForm):
    class Meta:
        model = TipoVehiculo
        fields = ['nombre', 'asientos_referencia', 'experiencia_minima_anios', 'categoria_licencia_minima', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El nombre es la clave usada por vehículos y solicitudes: no se edita.
        if self.instance.pk:
            self.fields['nombre'].disabled = True
