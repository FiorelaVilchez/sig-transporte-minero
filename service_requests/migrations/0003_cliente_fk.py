import django.db.models.deletion
from django.db import migrations, models


def textos_a_clientes(apps, schema_editor):
    Cliente = apps.get_model('crm', 'Cliente')
    Solicitud = apps.get_model('service_requests', 'SolicitudServicio')
    for solicitud in Solicitud.objects.all():
        nombre = ' '.join((solicitud.cliente or '').split()) or 'Cliente sin nombre'
        cliente = Cliente.objects.filter(razon_social__iexact=nombre).first()
        if cliente is None:
            cliente = Cliente.objects.create(razon_social=nombre)
        solicitud.cliente_ref = cliente
        solicitud.save(update_fields=['cliente_ref'])


def clientes_a_textos(apps, schema_editor):
    Solicitud = apps.get_model('service_requests', 'SolicitudServicio')
    for solicitud in Solicitud.objects.select_related('cliente_ref'):
        solicitud.cliente = solicitud.cliente_ref.razon_social
        solicitud.save(update_fields=['cliente'])


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
        ('service_requests', '0002_solicitudservicio_duracion_horas_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudservicio',
            name='cliente_ref',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='crm.cliente'),
        ),
        migrations.RunPython(textos_a_clientes, clientes_a_textos),
    ]
