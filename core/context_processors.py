from django.conf import settings


def sistema(request):
    """Datos del entorno que se muestran en la barra lateral (motor de base de datos real)."""
    motor = settings.DATABASES['default']['ENGINE'].rsplit('.', 1)[-1]
    nombres = {'sqlite3': 'SQLite', 'postgresql': 'PostgreSQL', 'mysql': 'MySQL'}
    return {'motor_bd': nombres.get(motor, motor)}
