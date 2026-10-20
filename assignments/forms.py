from django import forms

from .models import ChecklistPreoperacional, GastoServicio, Incidencia


class ChecklistForm(forms.ModelForm):
    class Meta:
        model = ChecklistPreoperacional
        fields = [
            'frenos', 'llantas', 'luces', 'cinturones', 'botiquin', 'extintor', 'radio_gps',
            'horas_sueno', 'km_inicial', 'observaciones',
        ]
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 2}),
            'horas_sueno': forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'max': '24'}),
        }


class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['tipo', 'gravedad', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


class GastoForm(forms.ModelForm):
    class Meta:
        model = GastoServicio
        fields = ['concepto', 'monto', 'detalle']

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor que cero.")
        return monto


class FinalizarForm(forms.Form):
    km_final = forms.IntegerField(min_value=0, label="Kilometraje final")

    def __init__(self, *args, km_inicial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.km_inicial = km_inicial

    def clean_km_final(self):
        km = self.cleaned_data['km_final']
        if self.km_inicial is not None and km < self.km_inicial:
            raise forms.ValidationError(f"Debe ser mayor o igual al kilometraje inicial ({self.km_inicial}).")
        return km
