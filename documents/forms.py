from django import forms

from .models import DocumentoConductor, DocumentoVehiculo, RequisitoDocumental


class _DocumentoBaseForm(forms.ModelForm):
    """Reglas comunes (M1): vencimiento según la matriz y visto bueno de mina."""

    APLICA_A = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_vencimiento'].required = False
        self.fields['fecha_vencimiento'].help_text = "Déjelo vacío solo para documentos que no vencen (por ejemplo, la tarjeta de propiedad)."
        self.fields['estado_mina'].help_text = "Si el requisito exige visto bueno de la mina, la asignación se bloquea (R8) mientras esté Pendiente u Observado."
        if not self.instance.pk:
            self.fields['estado_mina'].required = False

    def clean(self):
        datos = super().clean()
        tipo = datos.get('tipo_documento')
        emision = datos.get('fecha_emision')
        vencimiento = datos.get('fecha_vencimiento')
        if tipo and not vencimiento and tipo not in RequisitoDocumental.tipos_que_no_vencen(self.APLICA_A):
            self.add_error('fecha_vencimiento', "Este documento tiene fecha de vencimiento: ingrésela.")
        if emision and vencimiento and vencimiento < emision:
            self.add_error('fecha_vencimiento', "El vencimiento no puede ser anterior a la emisión.")
        if tipo:
            requiere = tipo in RequisitoDocumental.tipos_con_visto_bueno(self.APLICA_A)
            estado = datos.get('estado_mina')
            if not self.instance.pk and (not estado or estado == 'No requiere'):
                datos['estado_mina'] = 'Pendiente' if requiere else 'No requiere'
            elif self.instance.pk and requiere and estado == 'No requiere':
                datos['estado_mina'] = 'Pendiente'
            # Un documento renovado vuelve a revisión de la mina.
            if (self.instance.pk and requiere and 'fecha_vencimiento' in self.changed_data
                    and 'estado_mina' not in self.changed_data):
                datos['estado_mina'] = 'Pendiente'
        return datos


class DocumentoConductorForm(_DocumentoBaseForm):
    APLICA_A = 'Conductor'

    class Meta:
        model = DocumentoConductor
        fields = ['conductor', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'estado_mina', 'archivo']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class DocumentoVehiculoForm(_DocumentoBaseForm):
    APLICA_A = 'Vehículo'

    class Meta:
        model = DocumentoVehiculo
        fields = ['vehiculo', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'estado_mina', 'archivo']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
