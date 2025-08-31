"""
Unit tests for the GROBID client base ApiClient class.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from grobid_client.client import ApiClient


class TestApiClient:
    """Test cases for the base ApiClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:8070"
        self.username = "test_user"
        self.api_key = "test_key"
        self.status_endpoint = "isalive"
        self.timeout = 30

        self.client = ApiClient(
            base_url=self.base_url,
            username=self.username,
            api_key=self.api_key,
            status_endpoint=self.status_endpoint,
            timeout=self.timeout
        )

    def test_init(self):
        """Test ApiClient initialization."""
        assert self.client.base_url == self.base_url
        assert self.client.username == self.username
        assert self.client.api_key == self.api_key
        assert self.client.timeout == self.timeout
        assert self.client.status_endpoint == f"{self.base_url}/{self.status_endpoint}"

    def test_get_credentials(self):
        """Test get_credentials method."""
        credentials = self.client.get_credentials()
        expected = {"username": self.username, "api_key": self.api_key}
        assert credentials == expected

    def test_encode_with_data(self):
        """Test encode method with data."""
        mock_request = Mock()
        test_data = {"key": "value"}

        result = ApiClient.encode(mock_request, test_data)

        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == json.dumps(test_data)

    def test_encode_with_none(self):
        """Test encode method with None data."""
        mock_request = Mock()

        result = ApiClient.encode(mock_request, None)

        assert result == mock_request
        mock_request.add_header.assert_not_called()

    def test_decode_success(self):
        """Test decode method with successful JSON response."""
        mock_response = Mock()
        test_data = {"result": "success"}
        mock_response.json.return_value = test_data

        result = ApiClient.decode(mock_response)

        assert result == test_data

    def test_decode_failure(self):
        """Test decode method with JSON decode error."""
        mock_response = Mock()
        error = ValueError("Invalid JSON")
        error.message = "Invalid JSON"
        mock_response.json.side_effect = error

        result = ApiClient.decode(mock_response)

        assert result == "Invalid JSON"

    @patch('grobid_client.client.requests.request')
    def test_call_api_success(self, mock_request):
        """Test call_api method with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        url = "http://test.com/api"
        headers = {"Custom": "header"}
        params = {"param": "value"}
        data = {"data": "value"}
        files = {"file": "content"}

        response, status = self.client.call_api(
            method="POST",
            url=url,
            headers=headers,
            params=params,
            data=data,
            files=files,
            timeout=30
        )

        mock_request.assert_called_once_with(
            "POST",
            url,
            headers={"Custom": "header", "Accept": "application/xml"},
            params=params,
            files=files,
            data=data,
            timeout=30
        )
        assert response == mock_response
        assert status == 200

    @patch('grobid_client.client.requests.request')
    def test_get_method(self, mock_request):
        """Test GET method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        url = "http://test.com/api"
        params = {"param": "value"}

        response, status = self.client.get(url, params=params)

        mock_request.assert_called_once_with(
            "GET",
            url,
            headers={"Accept": "application/xml"},
            params=params,
            files={},
            data={},
            timeout=None
        )

    @patch('grobid_client.client.requests.request')
    def test_post_method(self, mock_request):
        """Test POST method."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        url = "http://test.com/api"
        data = {"key": "value"}
        files = {"file": "content"}

        response, status = self.client.post(url, data=data, files=files)

        mock_request.assert_called_once_with(
            "POST",
            url,
            headers={"Accept": "application/xml"},
            params={},
            files=files,
            data=data,
            timeout=None
        )

    @patch('grobid_client.client.requests.request')
    def test_put_method(self, mock_request):
        """Test PUT method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        url = "http://test.com/api"
        data = {"key": "updated_value"}

        response, status = self.client.put(url, data=data)

        mock_request.assert_called_once_with(
            "PUT",
            url,
            headers={"Accept": "application/xml"},
            params={},
            files={},
            data=data,
            timeout=None
        )

    @patch('grobid_client.client.requests.request')
    def test_delete_method(self, mock_request):
        """Test DELETE method."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        url = "http://test.com/api"

        response, status = self.client.delete(url)

        mock_request.assert_called_once_with(
            "DELETE",
            url,
            headers={"Accept": "application/xml"},
            params={},
            files={},
            data={},
            timeout=None
        )

    @patch('grobid_client.client.requests.request')
    def test_service_status(self, mock_request):
        """Test service_status method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        response, status = self.client.service_status()

        mock_request.assert_called_once_with(
            "GET",
            self.client.status_endpoint,
            headers={"Accept": "application/xml"},
            params={"format": "json"},
            files={},
            data={},
            timeout=None
        )


# ============================================================================
# COMPREHENSIVE TEST CLASSES
# ============================================================================


class TestApiClientInitialization:
    """Test cases for ApiClient initialization."""

    def test_init_with_minimal_parameters(self):
        """Test ApiClient initialization with minimal required parameters."""
        client = ApiClient(base_url="http://localhost:8070")
        
        assert client.base_url == "http://localhost:8070"
        assert client.username is None
        assert client.api_key is None
        assert client.timeout == 60
        assert client.accept_type == "application/xml"

    def test_init_with_all_parameters(self):
        """Test ApiClient initialization with all parameters."""
        client = ApiClient(
            base_url="http://test-server:8080",
            username="test_user",
            api_key="test_key",
            status_endpoint="health",
            timeout=120
        )
        
        assert client.base_url == "http://test-server:8080"
        assert client.username == "test_user"
        assert client.api_key == "test_key"
        assert client.timeout == 120
        assert client.status_endpoint == "http://test-server:8080/health"

    def test_init_with_none_values(self):
        """Test ApiClient initialization with None values."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username=None,
            api_key=None,
            status_endpoint=None,
            timeout=None
        )
        
        assert client.username is None
        assert client.api_key is None
        assert client.timeout is None

    def test_init_with_empty_strings(self):
        """Test ApiClient initialization with empty strings."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username="",
            api_key="",
            status_endpoint=""
        )
        
        assert client.username == ""
        assert client.api_key == ""
        assert client.status_endpoint == "http://localhost:8070"

    def test_init_with_negative_timeout(self):
        """Test ApiClient initialization with negative timeout."""
        client = ApiClient(
            base_url="http://localhost:8070",
            timeout=-10
        )
        
        assert client.timeout == -10

    def test_init_with_zero_timeout(self):
        """Test ApiClient initialization with zero timeout."""
        client = ApiClient(
            base_url="http://localhost:8070",
            timeout=0
        )
        
        assert client.timeout == 0


class TestApiClientCredentials:
    """Test cases for credential handling."""

    def test_get_credentials_with_both_username_and_api_key(self):
        """Test get_credentials method with both username and API key."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username="test_user",
            api_key="test_key"
        )
        
        credentials = client.get_credentials()
        expected = {"username": "test_user", "api_key": "test_key"}
        assert credentials == expected

    def test_get_credentials_with_only_username(self):
        """Test get_credentials method with only username."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username="test_user",
            api_key=None
        )
        
        credentials = client.get_credentials()
        expected = {"username": "test_user", "api_key": None}
        assert credentials == expected

    def test_get_credentials_with_only_api_key(self):
        """Test get_credentials method with only API key."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username=None,
            api_key="test_key"
        )
        
        credentials = client.get_credentials()
        expected = {"username": None, "api_key": "test_key"}
        assert credentials == expected

    def test_get_credentials_with_no_credentials(self):
        """Test get_credentials method with no credentials."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username=None,
            api_key=None
        )
        
        credentials = client.get_credentials()
        expected = {"username": None, "api_key": None}
        assert credentials == expected

    def test_get_credentials_with_empty_strings(self):
        """Test get_credentials method with empty string credentials."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username="",
            api_key=""
        )
        
        credentials = client.get_credentials()
        expected = {"username": "", "api_key": ""}
        assert credentials == expected

    def test_get_credentials_with_unicode_credentials(self):
        """Test get_credentials method with Unicode credentials."""
        client = ApiClient(
            base_url="http://localhost:8070",
            username="用户名",
            api_key="密码123"
        )
        
        credentials = client.get_credentials()
        expected = {"username": "用户名", "api_key": "密码123"}
        assert credentials == expected


class TestApiClientEncoding:
    """Test cases for request encoding."""

    def test_encode_with_valid_dict_data(self):
        """Test encode method with valid dictionary data."""
        mock_request = Mock()
        test_data = {"key": "value", "number": 123, "boolean": True}
        
        result = ApiClient.encode(mock_request, test_data)
        
        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == json.dumps(test_data)

    def test_encode_with_empty_dict(self):
        """Test encode method with empty dictionary."""
        mock_request = Mock()
        test_data = {}
        
        result = ApiClient.encode(mock_request, test_data)
        
        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == "{}"

    def test_encode_with_none_data(self):
        """Test encode method with None data."""
        mock_request = Mock()
        
        result = ApiClient.encode(mock_request, None)
        
        assert result == mock_request
        mock_request.add_header.assert_not_called()

    def test_encode_with_list_data(self):
        """Test encode method with list data."""
        mock_request = Mock()
        test_data = [1, 2, 3, "test"]
        
        result = ApiClient.encode(mock_request, test_data)
        
        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == json.dumps(test_data)

    def test_encode_with_string_data(self):
        """Test encode method with string data."""
        mock_request = Mock()
        test_data = "test string"
        
        result = ApiClient.encode(mock_request, test_data)
        
        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == json.dumps(test_data)

    def test_encode_with_nested_data(self):
        """Test encode method with nested data structures."""
        mock_request = Mock()
        test_data = {
            "user": {
                "name": "John",
                "age": 30,
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown"
                }
            },
            "items": [1, 2, 3]
        }
        
        result = ApiClient.encode(mock_request, test_data)
        
        mock_request.add_header.assert_called_once_with("Content-Type", "application/json")
        assert result.data == json.dumps(test_data)


class TestApiClientDecoding:
    """Test cases for response decoding."""

    def test_decode_with_valid_json_response(self):
        """Test decode method with valid JSON response."""
        mock_response = Mock()
        test_data = {"result": "success", "data": [1, 2, 3]}
        mock_response.json.return_value = test_data
        
        result = ApiClient.decode(mock_response)
        
        assert result == test_data
        mock_response.json.assert_called_once()

    def test_decode_with_empty_json_response(self):
        """Test decode method with empty JSON response."""
        mock_response = Mock()
        test_data = {}
        mock_response.json.return_value = test_data
        
        result = ApiClient.decode(mock_response)
        
        assert result == test_data

    def test_decode_with_string_json_response(self):
        """Test decode method with string JSON response."""
        mock_response = Mock()
        test_data = "test string"
        mock_response.json.return_value = test_data
        
        result = ApiClient.decode(mock_response)
        
        assert result == test_data

    def test_decode_with_json_decode_error(self):
        """Test decode method with JSON decode error."""
        mock_response = Mock()
        error = ValueError("Invalid JSON")
        error.message = "Invalid JSON"
        mock_response.json.side_effect = error
        
        result = ApiClient.decode(mock_response)
        
        assert result == "Invalid JSON"

    def test_decode_with_json_decode_error_no_message(self):
        """Test decode method with JSON decode error that has no message attribute."""
        mock_response = Mock()
        error = ValueError("Invalid JSON")
        # Remove message attribute to test fallback
        if hasattr(error, 'message'):
            delattr(error, 'message')
        mock_response.json.side_effect = error
        
        result = ApiClient.decode(mock_response)
        
        # Should return the error object itself
        assert result == error

    def test_decode_with_other_exception(self):
        """Test decode method with other types of exceptions."""
        mock_response = Mock()
        error = TypeError("Unexpected error")
        mock_response.json.side_effect = error
        
        result = ApiClient.decode(mock_response)
        
        # Should return the error object itself
        assert result == error


class TestApiClientCallApi:
    """Test cases for the call_api method."""

    @patch('grobid_client.client.requests.request')
    def test_call_api_success(self, mock_request):
        """Test call_api method with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="POST",
            url="http://test.com/api",
            headers={"Custom": "header"},
            params={"param": "value"},
            data={"data": "value"},
            files={"file": "content"},
            timeout=30
        )
        
        mock_request.assert_called_once_with(
            "POST",
            "http://test.com/api",
            headers={"Custom": "header", "Accept": "application/xml"},
            params={"param": "value"},
            files={"file": "content"},
            data={"data": "value"},
            timeout=30
        )
        assert response == mock_response
        assert status == 200

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_none_parameters(self, mock_request):
        """Test call_api method with None parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="GET",
            url="http://test.com/api",
            headers=None,
            params=None,
            data=None,
            files=None,
            timeout=None
        )
        
        mock_request.assert_called_once_with(
            "GET",
            "http://test.com/api",
            headers={"Accept": "application/xml"},
            params={},
            files={},
            data={},
            timeout=None
        )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_empty_parameters(self, mock_request):
        """Test call_api method with empty parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="GET",
            url="http://test.com/api",
            headers={},
            params={},
            data={},
            files={},
            timeout=60
        )
        
        mock_request.assert_called_once_with(
            "GET",
            "http://test.com/api",
            headers={"Accept": "application/xml"},
            params={},
            files={},
            data={},
            timeout=60
        )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_request_exception(self, mock_request):
        """Test call_api method with request exception."""
        mock_request.side_effect = requests.exceptions.RequestException("Request failed")
        
        client = ApiClient(base_url="http://localhost:8070")
        
        with pytest.raises(requests.exceptions.RequestException):
            client.call_api(
                method="GET",
                url="http://test.com/api"
            )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_timeout_exception(self, mock_request):
        """Test call_api method with timeout exception."""
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")
        
        client = ApiClient(base_url="http://localhost:8070")
        
        with pytest.raises(requests.exceptions.Timeout):
            client.call_api(
                method="GET",
                url="http://test.com/api",
                timeout=10
            )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_connection_error(self, mock_request):
        """Test call_api method with connection error."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = ApiClient(base_url="http://localhost:8070")
        
        with pytest.raises(requests.exceptions.ConnectionError):
            client.call_api(
                method="GET",
                url="http://test.com/api"
            )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_ssl_error(self, mock_request):
        """Test call_api method with SSL error."""
        mock_request.side_effect = requests.exceptions.SSLError("SSL certificate error")
        
        client = ApiClient(base_url="http://localhost:8070")
        
        with pytest.raises(requests.exceptions.SSLError):
            client.call_api(
                method="GET",
                url="http://test.com/api"
            )

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_http_error(self, mock_request):
        """Test call_api method with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="GET",
            url="http://test.com/api"
        )
        
        assert response == mock_response
        assert status == 404

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_500_error(self, mock_request):
        """Test call_api method with 500 error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="POST",
            url="http://test.com/api",
            data={"test": "data"}
        )
        
        assert response == mock_response
        assert status == 500


class TestApiClientHttpMethods:
    """Test cases for HTTP method wrappers."""

    @patch('grobid_client.client.ApiClient.call_api')
    def test_get_method(self, mock_call_api):
        """Test GET method."""
        mock_call_api.return_value = (Mock(), 200)
        
        client = ApiClient(base_url="http://localhost:8070")
        
        client.get("http://test.com/api", params={"param": "value"})
        
        mock_call_api.assert_called_once_with(
            "GET",
            "http://test.com/api",
            headers=None,
            params={"param": "value"},
            data=None,
            files=None,
            timeout=None
        )

    @patch('grobid_client.client.ApiClient.call_api')
    def test_post_method(self, mock_call_api):
        """Test POST method."""
        mock_call_api.return_value = (Mock(), 201)
        
        client = ApiClient(base_url="http://localhost:8070")
        
        client.post(
            "http://test.com/api",
            params={"param": "value"},
            data={"data": "value"},
            files={"file": "content"}
        )
        
        mock_call_api.assert_called_once_with(
            "POST",
            "http://test.com/api",
            headers=None,
            params={"param": "value"},
            data={"data": "value"},
            files={"file": "content"},
            timeout=None
        )

    @patch('grobid_client.client.ApiClient.call_api')
    def test_put_method(self, mock_call_api):
        """Test PUT method."""
        mock_call_api.return_value = (Mock(), 200)
        
        client = ApiClient(base_url="http://localhost:8070")
        
        client.put(
            "http://test.com/api",
            params={"param": "value"},
            data={"data": "value"},
            files={"file": "content"}
        )
        
        mock_call_api.assert_called_once_with(
            "PUT",
            "http://test.com/api",
            headers=None,
            params={"param": "value"},
            data={"data": "value"},
            files={"file": "content"},
            timeout=None
        )

    @patch('grobid_client.client.ApiClient.call_api')
    def test_delete_method(self, mock_call_api):
        """Test DELETE method."""
        mock_call_api.return_value = (Mock(), 204)
        
        client = ApiClient(base_url="http://localhost:8070")
        
        client.delete("http://test.com/api", params={"param": "value"})
        
        mock_call_api.assert_called_once_with(
            "DELETE",
            "http://test.com/api",
            headers=None,
            params={"param": "value"},
            data=None,
            files=None,
            timeout=None
        )

    @patch('grobid_client.client.ApiClient.call_api')
    def test_http_methods_with_kwargs(self, mock_call_api):
        """Test HTTP methods with additional kwargs."""
        mock_call_api.return_value = (Mock(), 200)
        
        client = ApiClient(base_url="http://localhost:8070")
        
        # Test with timeout kwarg
        client.get("http://test.com/api", timeout=30)
        
        mock_call_api.assert_called_once_with(
            "GET",
            "http://test.com/api",
            headers=None,
            params=None,
            data=None,
            files=None,
            timeout=30
        )


class TestApiClientServiceStatus:
    """Test cases for service status method."""

    @patch('grobid_client.client.ApiClient.call_api')
    def test_service_status(self, mock_call_api):
        """Test service_status method."""
        mock_call_api.return_value = (Mock(), 200)
        
        client = ApiClient(
            base_url="http://localhost:8070",
            status_endpoint="health"
        )
        
        client.service_status()
        
        mock_call_api.assert_called_once_with(
            "GET",
            "http://localhost:8070/health",
            headers=None,
            params={"format": "json"},
            data=None,
            files=None,
            timeout=None
        )

    @patch('grobid_client.client.ApiClient.call_api')
    def test_service_status_with_kwargs(self, mock_call_api):
        """Test service_status method with kwargs."""
        mock_call_api.return_value = (Mock(), 200)
        
        client = ApiClient(
            base_url="http://localhost:8070",
            status_endpoint="health"
        )
        
        client.service_status(timeout=30)
        
        mock_call_api.assert_called_once_with(
            "GET",
            "http://localhost:8070/health",
            headers=None,
            params={"format": "json"},
            data=None,
            files=None,
            timeout=30
        )


class TestApiClientEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_init_with_special_characters_in_url(self):
        """Test initialization with special characters in URL."""
        client = ApiClient(
            base_url="http://test-server:8080/path/with/slashes",
            status_endpoint="health/check"
        )
        
        assert client.base_url == "http://test-server:8080/path/with/slashes"
        assert client.status_endpoint == "http://test-server:8080/path/with/slashes/health/check"

    def test_init_with_unicode_characters(self):
        """Test initialization with Unicode characters."""
        client = ApiClient(
            base_url="http://test-server:8080",
            username="用户名",
            api_key="密码"
        )
        
        assert client.username == "用户名"
        assert client.api_key == "密码"

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_unicode_data(self, mock_request):
        """Test call_api method with Unicode data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        unicode_data = {"message": "Hello 世界", "user": "用户名"}
        
        response, status = client.call_api(
            method="POST",
            url="http://test.com/api",
            data=unicode_data
        )
        
        # Should handle Unicode data correctly
        assert response == mock_response
        assert status == 200

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_large_data(self, mock_request):
        """Test call_api method with large data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        large_data = {"large_field": "x" * 10000}
        
        response, status = client.call_api(
            method="POST",
            url="http://test.com/api",
            data=large_data
        )
        
        # Should handle large data correctly
        assert response == mock_response
        assert status == 200

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_empty_string_url(self, mock_request):
        """Test call_api method with empty string URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        response, status = client.call_api(
            method="GET",
            url=""
        )
        
        # Should handle empty URL
        assert response == mock_response
        assert status == 200

    @patch('grobid_client.client.requests.request')
    def test_call_api_with_very_long_url(self, mock_request):
        """Test call_api method with very long URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ApiClient(base_url="http://localhost:8070")
        
        long_url = "http://test.com/api/" + "a" * 1000
        
        response, status = client.call_api(
            method="GET",
            url=long_url
        )
        
        # Should handle long URL
        assert response == mock_response
        assert status == 200

