from unittest.mock import Mock, patch

from ai.api.aws.wca_secret_manager import WcaSecretManagerError
from ai.api.model_client.exceptions import ModelTimeoutError
from ai.api.model_client.wca_client import WCAClient
from botocore.exceptions import ClientError
from django.test import override_settings
from requests.exceptions import ReadTimeout
from test_utils import WisdomServiceLogAwareTestCase


class MockResponse:
    def __init__(self, json, status_code):
        self._json = json
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        return


class TestWCAClient(WisdomServiceLogAwareTestCase):
    def test_get_token(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": "abcdef"}
        response = MockResponse(
            json={
                "access_token": "access_token",
                "refresh_token": "not_supported",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expiration": 1691445310,
                "scope": "ibm openid",
            },
            status_code=200,
        )

        model_client = WCAClient(inference_url='http://example.com/')
        model_client.session.post = Mock(return_value=response)

        model_client.get_token('abcdef')

        model_client.session.post.assert_called_once_with(
            "https://iam.cloud.ibm.com/identity/token",
            headers=headers,
            data=data,
        )

    def test_infer(self):
        model_name = "zavala"
        context = "null"
        prompt = "- name: install ffmpeg on Red Hat Enterprise Linux"

        model_input = {
            "instances": [
                {
                    "context": context,
                    "prompt": prompt,
                }
            ]
        }
        data = {
            "model_id": model_name,
            "prompt": f"{context}{prompt}\n",
        }
        token = {
            "access_token": "access_token",
            "refresh_token": "not_supported",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expiration": 1691445310,
            "scope": "ibm openid",
        }
        predictions = {"predictions": ["      ansible.builtin.apt:\n        name: apache2"]}
        response = MockResponse(
            json=predictions,
            status_code=200,
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token['access_token']}",
        }

        model_client = WCAClient(inference_url='https://example.com')
        model_client.session.post = Mock(return_value=response)
        model_client.get_token = Mock(return_value=token)
        model_client.get_model_id = Mock(return_value=model_name)

        result = model_client.infer(model_input=model_input, model_name=model_name)

        model_client.get_token.assert_called_once()
        model_client.session.post.assert_called_once_with(
            "https://example.com/v1/wca/codegen/ansible",
            headers=headers,
            json=data,
            timeout=None,
        )
        self.assertEqual(result, predictions)

    def test_infer_timeout(self):
        model_name = "zavala"
        model_input = {
            "instances": [
                {
                    "context": "null",
                    "prompt": "- name: install ffmpeg on Red Hat Enterprise Linux",
                }
            ]
        }
        token = {
            "access_token": "access_token",
            "refresh_token": "not_supported",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expiration": 1691445310,
            "scope": "ibm openid",
        }
        model_client = WCAClient(inference_url='https://example.com')
        model_client.get_token = Mock(return_value=token)
        model_client.session.post = Mock(side_effect=ReadTimeout())
        model_client.get_model_id = Mock(return_value=model_name)
        with self.assertRaises(ModelTimeoutError):
            model_client.infer(model_input=model_input, model_name=model_name)

    @override_settings(ANSIBLE_WCA_FREE_API_KEY='abcdef')
    def test_get_api_key_without_seat(self):
        model_client = WCAClient(inference_url='http://example.com/')
        api_key = model_client.get_api_key(False, None)
        self.assertEqual(api_key, 'abcdef')

    @override_settings(ANSIBLE_WCA_FREE_API_KEY='abcdef')
    def test_get_api_key_with_seat_without_org_id(self):
        model_client = WCAClient(inference_url='http://example.com/')
        api_key = model_client.get_api_key(True, None)
        self.assertEqual(api_key, 'abcdef')

    @override_settings(WCA_SECRET_MANAGER_PRIMARY_REGION='us-east-1')
    @patch('ai.api.aws.wca_secret_manager.WcaSecretManager.get_client')
    def test_get_api_key_from_aws(self, m_get_client):
        secret_value = "1234567"
        m_boto3_client = Mock()
        m_boto3_client.get_secret_value.return_value = {"SecretString": secret_value}
        m_get_client.return_value = m_boto3_client

        model_client = WCAClient(inference_url='http://example.com/')
        api_key = model_client.get_api_key(True, secret_value)
        self.assertEqual(api_key, secret_value)
        m_boto3_client.get_secret_value.assert_called()

    @patch('ai.api.aws.wca_secret_manager.WcaSecretManager.get_client')
    def test_get_api_key_from_aws_error(self, m_get_client):
        m_boto3_client = Mock()
        m_boto3_client.exceptions.ResourceNotFoundException = Exception
        m_boto3_client.get_secret_value.side_effect = ClientError
        m_get_client.return_value = m_boto3_client

        model_client = WCAClient(inference_url='http://example.com/')
        with self.assertRaises(WcaSecretManagerError):
            model_client.get_api_key(True, '1234567')
