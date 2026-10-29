from django.test import SimpleTestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from .services.access import scope

class AccessScopeTests(SimpleTestCase):
    def setUp(self): self.factory=RequestFactory()
    def test_anonymous_denied(self):
        request=self.factory.get('/intercultural/')
        request.user=AnonymousUser()
        with self.assertRaises(PermissionDenied): scope(request)
