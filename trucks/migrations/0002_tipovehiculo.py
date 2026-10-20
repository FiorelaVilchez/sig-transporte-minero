from django.db import migrations, models


def cargar_catalogo(apps, schema_editor):
    from trucks.catalogo import TIPOS_INICIALES
    TipoVehiculo = apps.get_model('trucks', 'TipoVehiculo')
    Vehiculo = apps.get_model('trucks', 'Vehiculo')
    for nombre, asientos, exp, cat, activo in TIPOS_INICIALES:
        TipoVehiculo.objects.get_or_create(
            nombre=nombre,
            defaults={'asientos_referencia': asientos, 'experiencia_minima_anios': exp,
                      'categoria_licencia_minima': cat, 'activo': activo},
        )
    # Cualquier tipo escrito en registros existentes también pasa al catálogo.
    for nombre in Vehiculo.objects.values_list('tipo', flat=True).distinct():
        if nombre:
            TipoVehiculo.objects.get_or_create(nombre=nombre)


class Migration(migrations.Migration):

    dependencies = [
        ('trucks', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoVehiculo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, unique=True, verbose_name='Nombre del tipo')),
                ('asientos_referencia', models.PositiveIntegerField(default=4, verbose_name='Asientos de referencia')),
                ('experiencia_minima_anios', models.PositiveIntegerField(default=0, verbose_name='Experiencia mínima (años de licencia)')),
                ('categoria_licencia_minima', models.CharField(choices=[('A-I', 'A-I'), ('A-IIa', 'A-IIa'), ('A-IIb', 'A-IIb'), ('A-IIIa', 'A-IIIa'), ('A-IIIb', 'A-IIIb'), ('A-IIIc', 'A-IIIc')], default='A-I', max_length=10, verbose_name='Categoría mínima de licencia')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={
                'verbose_name': 'Tipo de vehículo',
                'verbose_name_plural': 'Tipos de vehículo',
                'ordering': ['asientos_referencia', 'nombre'],
            },
        ),
        migrations.RunPython(cargar_catalogo, migrations.RunPython.noop),
    ]
