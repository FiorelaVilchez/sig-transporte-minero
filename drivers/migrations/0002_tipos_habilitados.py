from django.db import migrations, models


def mapear_especialidad(apps, schema_editor):
    """Marca los tipos habilitados a partir del texto libre de especialidad."""
    Conductor = apps.get_model('drivers', 'Conductor')
    TipoVehiculo = apps.get_model('trucks', 'TipoVehiculo')
    tipos = list(TipoVehiculo.objects.all())
    for conductor in Conductor.objects.all():
        texto = (conductor.especialidad or '').lower()
        for tipo in tipos:
            if tipo.nombre.lower() in texto:
                conductor.tipos_habilitados.add(tipo)


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0001_initial'),
        ('trucks', '0002_tipovehiculo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conductor',
            name='especialidad',
            field=models.CharField(blank=True, max_length=100, verbose_name='Especialidad (texto, versión 1.0)'),
        ),
        migrations.AddField(
            model_name='conductor',
            name='categoria_licencia',
            field=models.CharField(blank=True, choices=[('A-I', 'A-I'), ('A-IIa', 'A-IIa'), ('A-IIb', 'A-IIb'), ('A-IIIa', 'A-IIIa'), ('A-IIIb', 'A-IIIb'), ('A-IIIc', 'A-IIIc')], max_length=10, verbose_name='Categoría de licencia'),
        ),
        migrations.AddField(
            model_name='conductor',
            name='fecha_obtencion_licencia',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de obtención de la licencia'),
        ),
        migrations.AddField(
            model_name='conductor',
            name='tipos_habilitados',
            field=models.ManyToManyField(blank=True, related_name='conductores_habilitados', to='trucks.tipovehiculo', verbose_name='Tipos de vehículo que puede manejar'),
        ),
        migrations.RunPython(mapear_especialidad, migrations.RunPython.noop),
    ]
