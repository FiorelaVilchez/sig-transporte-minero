from django import forms

from trucks.models import TipoVehiculo

from .models import Conductor


class ConductorForm(forms.ModelForm):
    tipos_habilitados = forms.ModelMultipleChoiceField(
        queryset=TipoVehiculo.objects.filter(activo=True),
        to_field_name='nombre',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Tipos de vehículo que puede manejar",
        error_messages={'required': "Marque al menos un tipo de vehículo."},
    )

    class Meta:
        model = Conductor
        fields = [
            'nombres', 'apellidos', 'dni', 'licencia',
            'categoria_licencia', 'fecha_obtencion_licencia', 'tipos_habilitados',
            'estado', 'telefono', 'fecha_nacimiento', 'fecha_ingreso',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_obtencion_licencia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el conductor tiene marcado un tipo ya inactivo, se sigue mostrando.
        if self.instance.pk:
            self.fields['tipos_habilitados'].queryset = TipoVehiculo.objects.filter(
                activo=True
            ) | self.instance.tipos_habilitados.all()
            self.fields['tipos_habilitados'].queryset = self.fields['tipos_habilitados'].queryset.distinct()
        self.fields['categoria_licencia'].required = True
        self.fields['fecha_obtencion_licencia'].required = True

    def clean(self):
        datos = super().clean()
        categoria = datos.get('categoria_licencia')
        tipos = datos.get('tipos_habilitados') or []
        if categoria:
            insuficientes = [
                t.nombre for t in tipos
                if TipoVehiculo.orden_categoria(categoria) < TipoVehiculo.orden_categoria(t.categoria_licencia_minima)
            ]
            if insuficientes:
                self.add_error(
                    'tipos_habilitados',
                    f"La licencia {categoria} no alcanza para: {', '.join(insuficientes)}.",
                )
        return datos

    def save(self, commit=True):
        conductor = super().save(commit=commit)
        # Se conserva un texto legible para reportes y compatibilidad con la versión 1.0.
        tipos = self.cleaned_data.get('tipos_habilitados') or []
        conductor.especialidad = ", ".join(t.nombre for t in tipos)[:100]
        if commit:
            conductor.save(update_fields=['especialidad', 'updated_at'])
        return conductor
