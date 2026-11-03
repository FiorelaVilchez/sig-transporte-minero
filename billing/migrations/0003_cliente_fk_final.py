import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_cliente_fk'),
    ]

    operations = [
        migrations.RemoveField(model_name='tarifa', name='cliente'),
        migrations.RenameField(model_name='tarifa', old_name='cliente_ref', new_name='cliente'),
        migrations.AlterField(
            model_name='tarifa',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tarifas', to='crm.cliente', verbose_name='Cliente'),
        ),
        migrations.AddConstraint(
            model_name='tarifa',
            constraint=models.UniqueConstraint(fields=('cliente', 'tipo_vehiculo'), name='tarifa_unica_cliente_tipo'),
        ),
        migrations.AlterModelOptions(
            name='tarifa',
            options={'ordering': ['cliente__razon_social', 'tipo_vehiculo__asientos_referencia'], 'verbose_name': 'Tarifa', 'verbose_name_plural': 'Tarifas'},
        ),
    ]
