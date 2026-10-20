from django import forms

from billing.models import Tarifa
from documents.models import DocumentoConductor, DocumentoVehiculo, RequisitoDocumental
from trucks.forms import TipoVehiculoForm  # noqa: F401  (se reexporta para Configuración)
from trucks.models import TipoVehiculo


class RequisitoForm(forms.ModelForm):
    tipo_documento = forms.ChoiceField(
        label="Tipo de documento",
        choices=[
            ('Conductor', DocumentoConductor.TIPO_DOCUMENTO_CHOICES),
            ('Vehículo', DocumentoVehiculo.TIPO_DOCUMENTO_CHOICES),
        ],
    )

    class Meta:
        model = RequisitoDocumental
        fields = ['aplica_a', 'tipo_documento', 'bloqueante', 'vence', 'requiere_visto_bueno_mina', 'tipos_vehiculo', 'activo']
        widgets = {'tipos_vehiculo': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipos_vehiculo'].queryset = TipoVehiculo.objects.filter(activo=True)
        self.fields['tipos_vehiculo'].help_text = "Déjelo sin marcar para que aplique a todos los tipos."

    def clean(self):
        datos = super().clean()
        aplica, tipo = datos.get('aplica_a'), datos.get('tipo_documento')
        validos = {
            'Conductor': dict(DocumentoConductor.TIPO_DOCUMENTO_CHOICES),
            'Vehículo': dict(DocumentoVehiculo.TIPO_DOCUMENTO_CHOICES),
        }
        if aplica and tipo and tipo not in validos.get(aplica, {}):
            self.add_error('tipo_documento', f"'{tipo}' no es un documento de {aplica.lower()}.")
        return datos


class TarifaForm(forms.ModelForm):
    class Meta:
        model = Tarifa
        fields = ['cliente', 'tipo_vehiculo', 'tarifa_base', 'km_incluidos', 'precio_km_adicional', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_vehiculo'].queryset = TipoVehiculo.objects.filter(activo=True)
