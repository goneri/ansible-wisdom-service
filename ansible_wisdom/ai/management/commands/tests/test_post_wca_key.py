from io import StringIO
from unittest.mock import patch

from ai.api.aws.wca_secret_manager import Suffixes
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class PostWcaKeyCommandTestCase(TestCase):
    def test_missing_required_args(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: org_id, secret'
        ):
            call_command('post_wca_key')

    @patch("ai.management.commands._base_wca_command.WcaSecretManager")
    def test_key_saved(self, mock_secret_manager):
        instance = mock_secret_manager.return_value
        instance.save_secret.return_value = "mock_key_name"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('post_wca_key', 'mock_org_id', 'mock_key')
            instance.save_secret.assert_called_once_with(
                "mock_org_id", Suffixes.API_KEY, "mock_key"
            )
            captured_output = mock_stdout.getvalue()
            self.assertIn(
                "API Key for orgId 'mock_org_id' stored as: mock_key_name", captured_output
            )