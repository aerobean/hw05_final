from http import HTTPStatus

from django.test import TestCase


class ErrorTemplateTestClass(TestCase):
    def test_404_error_page(self):
        response = self.client.get('/nonexisting-page/')
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND
        )
        self.assertTemplateUsed(response, 'core/404.html')
