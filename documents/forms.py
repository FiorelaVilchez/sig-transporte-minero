from django import forms
from .models import DocumentoConductor, DocumentoVehiculo

class DocumentoConductorForm(forms.ModelForm):
    class Meta:
        model = DocumentoConductor
        fields = ['conductor', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'archivo']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

class DocumentoVehiculoForm(forms.ModelForm):
    class Meta:
        model = DocumentoVehiculo
        fields = ['vehiculo', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'archivo']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }
