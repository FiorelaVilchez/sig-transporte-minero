from django import forms

from .models import ReporteGerencial


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data if item]
        if not data:
            return []
        return [single_file_clean(data, initial)]


class ReporteGerencialForm(forms.ModelForm):
    capturas = MultipleFileField(
        required=False,
        label="Capturas de pantalla",
        help_text=(
            "Opcional. Puede subir varias imágenes (PNG, JPG) en lugar de o además del PDF. "
            "Mantenga presionada Ctrl (Windows) o Cmd (Mac) para seleccionar varios archivos."
        ),
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True,
        }),
    )

    class Meta:
        model = ReporteGerencial
        fields = ['descripcion', 'archivo_pdf']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dashboard gerencial - Sprint 5',
            }),
            'archivo_pdf': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf,.pdf',
            }),
        }
        help_texts = {
            'archivo_pdf': 'Opcional. PDF exportado desde Power BI Desktop (Archivo → Exportar → Exportar a PDF).',
        }

    def clean(self):
        cleaned_data = super().clean()
        archivo_pdf = cleaned_data.get('archivo_pdf')
        capturas = self.files.getlist('capturas')

        if not archivo_pdf and not capturas:
            raise forms.ValidationError(
                'Debe subir al menos un archivo PDF o una captura de pantalla.'
            )
        return cleaned_data
