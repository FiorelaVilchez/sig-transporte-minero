import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import PerfilUsuario
from drivers.models import Conductor
from trucks.models import Vehiculo
from documents.models import DocumentoConductor, DocumentoVehiculo

class DocumentoViewsTestCase(TestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(username='admin', password='password')
        PerfilUsuario.objects.create(usuario=self.admin_user, rol='Administrador de operaciones')
        
        self.supervisor_user = User.objects.create_user(username='supervisor', password='password')
        PerfilUsuario.objects.create(usuario=self.supervisor_user, rol='Supervisor')
        
        self.gerencia_user = User.objects.create_user(username='gerencia', password='password')
        PerfilUsuario.objects.create(usuario=self.gerencia_user, rol='Gerencia')

        # Create driver and vehicle
        self.conductor = Conductor.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            licencia="Q12345678",
            especialidad="Camión",
            estado="Disponible",
            dni="12345678",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )
        self.vehiculo = Vehiculo.objects.create(
            placa="ABC-123",
            tipo="Camioneta",
            capacidad=5,
            estado="Disponible",
            revision_tecnica_vigente=True,
            seguro_vigente=True,
        )

        self.mock_file = SimpleUploadedFile("test_doc.pdf", b"file_content", content_type="application/pdf")

    def test_document_list_permissions(self):
        # Admin can view
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('documents:document_list'))
        self.assertEqual(response.status_code, 200)

        # Supervisor can view/edit
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('documents:document_list'))
        self.assertEqual(response.status_code, 200)

        # Gerencia cannot view (403)
        self.client.force_login(self.gerencia_user)
        response = self.client.get(reverse('documents:document_list'))
        self.assertEqual(response.status_code, 403)

    def test_auto_recalculation_on_save(self):
        # Create a document that is vencido
        doc = DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=datetime.date.today() - datetime.timedelta(days=100),
            fecha_vencimiento=datetime.date.today() - datetime.timedelta(days=5),
        )
        # Should be Vencido because of model save override
        self.assertEqual(doc.estado_documento, "Vencido")

        # Update date to future -> Vigente
        doc.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=100)
        doc.save()
        self.assertEqual(doc.estado_documento, "Vigente")

    def test_create_document_views(self):
        self.client.force_login(self.supervisor_user)
        
        # Post conductor document
        post_data = {
            'conductor': self.conductor.pk,
            'tipo_documento': 'Examen médico',
            'fecha_emision': '2026-01-01',
            'fecha_vencimiento': '2026-07-20',
            'archivo': self.mock_file
        }
        response = self.client.post(reverse('documents:documento_conductor_create'), post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify saved document has calculated state
        doc = DocumentoConductor.objects.get(tipo_documento='Examen médico')
        self.assertIsNotNone(doc.archivo)
        self.assertTrue(doc.estado_documento in ['Vigente', 'Por vencer', 'Vencido'])
