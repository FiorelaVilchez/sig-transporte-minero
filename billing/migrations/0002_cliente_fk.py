import django.db.models.deletion
from django.db import migrations, models


def textos_a_clientes(apps, schema_editor):
    Cliente = apps.get_model('crm', 'Cliente')
    Tarifa = apps.get_model('billing', 'Tarifa')
    for tarifa in Tarifa.objects.all():
        nombre = ' '.join((tarifa.cliente or '').split()) or 'Cliente sin nombre'
        cliente = Cliente.objects.filter(razon_social__iexact=nombre).first()
        if cliente is None:
            cliente = Cliente.objects.create(razon_social=nombre)
        tarifa.cliente_ref = cliente
        tarifa.save(update_fields=['cliente_ref'])


def clientes_a_textos(apps, schema_editor):
    Tarifa = apps.get_model('billing', 'Tarifa')
    for tarifa in Tarifa.objects.select_related('cliente_ref'):
        tarifa.cliente = tarifa.cliente_ref.razon_social
        tarifa.save(update_fields=['cliente'])


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(model_name='tarifa', name='tarifa_unica_cliente_tipo'),
        migrations.AddField(
            model_name='tarifa',
            name='cliente_ref',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='crm.cliente'),
        ),
        migrations.RunPython(textos_a_clientes, clientes_a_textos),
    ]
