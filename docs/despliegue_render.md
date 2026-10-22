# Despliegue de demostración en Render

El repositorio trae todo lo necesario para publicar el sistema en Render con el plan gratuito:
`render.yaml` (servicio web y base PostgreSQL), `build.sh` (dependencias, estáticos, migraciones y
datos de demostración) y el comando `preparar_demo`.

## Pasos

1. Crear una cuenta en https://render.com (se puede entrar con GitHub).
2. New > Blueprint, elegir el repositorio `sig-transporte-minero` y pulsar Apply.
3. Esperar a que termine el primer despliegue (unos 5 minutos). El enlace aparece en el servicio
   `sig-transporte-minero`, con la forma `https://sig-transporte-minero-xxxx.onrender.com`.
4. Entrar con los usuarios de prueba de `seed_users`.

## Qué tener en cuenta

- El plan gratuito apaga el servicio tras 15 minutos sin visitas; la siguiente visita tarda cerca de
  un minuto en cargar. Abrir el enlace unos minutos antes de usarlo.
- La base gratuita vence a los 30 días de creada. Después se crea otra (Apply de nuevo) y los datos
  de demostración se cargan solos.
- Los archivos subidos se pierden cuando el servicio se reinicia.
- Para recargar los datos de demostración (por ejemplo, para que las fechas queden alrededor del día
  de una exposición): en Environment poner `RECARGAR_DEMO=1`, guardar y hacer Manual Deploy. Luego
  volver a `0` para que un despliegue posterior no borre lo que se haya registrado.
- Es un despliegue de demostración. Para usarlo con datos reales: servidor propio o VPS, dominio,
  contraseñas nuevas, respaldos y sin `seed_data`.
