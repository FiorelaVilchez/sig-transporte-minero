import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service_requests', '0003_cliente_fk'),
    ]

    operations = [
        migrations.RemoveField(model_name='solicitudservicio', name='cliente'),
        migrations.RenameField(model_name='solicitudservicio', old_name='cliente_ref', new_name='cliente'),
        migrations.AlterField(
            model_name='solicitudservicio',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='solicitudes', to='crm.cliente', verbose_name='Cliente'),
        ),
    ]
