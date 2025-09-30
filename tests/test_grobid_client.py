"""
Unit tests for the GROBID client main functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import json
import os
import tempfile
import logging
import requests
from io import StringIO

from grobid_client.grobid_client import GrobidClient, ServerUnavailableException


class TestGrobidClient:
    """Test cases for the GrobidClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_config = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 1000,
            'coordinates': ["persName", "figure", "ref"],
            'sleep_time': 5,
            'timeout': 60,
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }

    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    def test_init_default_values(self, mock_configure_logging, mock_test_server):
        """Test GrobidClient initialization with default values."""
        mock_test_server.return_value = (True, 200)

        client = GrobidClient(check_server=False)

        assert client.config['grobid_server'] == 'http://localhost:8070'
        assert client.config['batch_size'] == 10
        assert client.config['sleep_time'] == 5
        assert client.config['timeout'] == 180
        assert 'persName' in client.config['coordinates']
        mock_configure_logging.assert_called_once()

    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    def test_init_custom_values(self, mock_configure_logging, mock_test_server):
        """Test GrobidClient initialization with custom values."""
        mock_test_server.return_value = (True, 200)

        custom_coords = ["figure", "ref"]
        client = GrobidClient(
            grobid_server='http://custom:9090',
            batch_size=500,
            coordinates=custom_coords,
            sleep_time=10,
            timeout=120,
            check_server=False
        )

        assert client.config['grobid_server'] == 'http://custom:9090'
        assert client.config['batch_size'] == 500
        assert client.config['coordinates'] == custom_coords
        assert client.config['sleep_time'] == 10
        assert client.config['timeout'] == 120

    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    @patch('grobid_client.grobid_client.GrobidClient._load_config')
    def test_init_with_config_path(self, mock_load_config, mock_configure_logging, mock_test_server):
        """Test GrobidClient initialization with config file path."""
        mock_test_server.return_value = (True, 200)

        config_path = '/path/to/config.json'
        client = GrobidClient(config_path=config_path, check_server=False)

        mock_load_config.assert_called_once_with(config_path)
        mock_configure_logging.assert_called_once()

    def test_parse_file_size_various_formats(self):
        """Test _parse_file_size method with various input formats."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

        # Test various formats
        assert client._parse_file_size('10MB') == 10 * 1024 * 1024
        assert client._parse_file_size('1GB') == 1024 * 1024 * 1024
        assert client._parse_file_size('500KB') == 500 * 1024
        assert client._parse_file_size('2TB') == 2 * 1024 ** 4
        assert client._parse_file_size('100') == 100
        assert client._parse_file_size('50B') == 50

        # Test invalid format (should return default 10MB)
        assert client._parse_file_size('invalid') == 10 * 1024 * 1024

    @patch('builtins.open', new_callable=mock_open, read_data='{"grobid_server": "http://test:8080"}')
    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    def test_load_config_success(self, mock_configure_logging, mock_test_server, mock_file):
        """Test successful configuration loading."""
        mock_test_server.return_value = (True, 200)

        client = GrobidClient(check_server=False)
        client._load_config('/path/to/config.json')

        mock_file.assert_called_once_with('/path/to/config.json', 'r')
        assert client.config['grobid_server'] == 'http://test:8080'

    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    def test_load_config_file_not_found(self, mock_configure_logging, mock_test_server):
        """Test configuration loading with missing file."""
        mock_test_server.return_value = (True, 200)

        client = GrobidClient(check_server=False)

        with pytest.raises(FileNotFoundError):
            client._load_config('/nonexistent/config.json')

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('grobid_client.grobid_client.GrobidClient._test_server_connection')
    @patch('grobid_client.grobid_client.GrobidClient._configure_logging')
    def test_load_config_invalid_json(self, mock_configure_logging, mock_test_server, mock_file):
        """Test configuration loading with invalid JSON."""
        mock_test_server.return_value = (True, 200)

        client = GrobidClient(check_server=False)

        with pytest.raises(json.JSONDecodeError):
            client._load_config('/path/to/config.json')

    @patch('grobid_client.grobid_client.requests.get')
    def test_test_server_connection_success(self, mock_get):
        """Test successful server connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
            client = GrobidClient(check_server=False)
            client.logger = Mock()

            is_available, status = client._test_server_connection()

            assert is_available is True
            assert status == 200
            client.logger.info.assert_called()

    @patch('grobid_client.grobid_client.requests.get')
    def test_test_server_connection_failure(self, mock_get):
        """Test failed server connection test."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
            client = GrobidClient(check_server=False)
            client.logger = Mock()

            is_available, status = client._test_server_connection()

            assert is_available is False
            assert status == 500
            client.logger.error.assert_called()

    @patch('grobid_client.grobid_client.requests.get')
    def test_test_server_connection_exception(self, mock_get):
        """Test server connection test with request exception."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
            client = GrobidClient(check_server=False)
            client.logger = Mock()

            with pytest.raises(ServerUnavailableException):
                client._test_server_connection()

    def test_output_file_name_with_output_path(self):
        """Test _output_file_name method with output path."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

        input_file = '/input/path/document.pdf'
        input_path = '/input/path'
        output_path = '/output/path'

        result = client._output_file_name(input_file, input_path, output_path)
        expected = '/output/path/document.grobid.tei.xml'

        assert result == expected

    def test_output_file_name_without_output_path(self):
        """Test _output_file_name method without output path."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

        input_file = '/input/path/document.pdf'
        input_path = '/input/path'
        output_path = None

        result = client._output_file_name(input_file, input_path, output_path)
        expected = '/input/path/document.grobid.tei.xml'

        assert result == expected

    def test_get_server_url(self):
        """Test get_server_url method."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

        service = 'processFulltextDocument'
        result = client.get_server_url(service)
        expected = 'http://localhost:8070/api/processFulltextDocument'

        assert result == expected

    def test_ping_method(self):
        """Test ping method."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection') as mock_test:
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                mock_test.return_value = (True, 200)
                client = GrobidClient(check_server=False)

                result = client.ping()

                assert result == (True, 200)

    @patch('os.walk')
    def test_process_no_files_found(self, mock_walk):
        """Test process method when no eligible files are found."""
        mock_walk.return_value = [('/test/path', [], [])]

        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)
                client.logger = Mock()

                client.process('processFulltextDocument', '/test/path')

                client.logger.warning.assert_called_with('No eligible files found in /test/path')

    @patch('os.walk')
    def test_process_with_pdf_files(self, mock_walk):
        """Test process method with PDF files."""
        mock_walk.return_value = [
            ('/test/path', [], ['doc1.pdf', 'doc2.PDF', 'not_pdf.txt'])
        ]

        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                with patch('grobid_client.grobid_client.GrobidClient.process_batch') as mock_batch:
                    mock_batch.return_value = (2, 0)  # Return tuple as expected
                    client = GrobidClient(check_server=False)
                    client.logger = Mock()

                    client.process('processFulltextDocument', '/test/path')

                    mock_batch.assert_called_once()
                    client.logger.info.assert_any_call('Found 2 file(s) to process')

    @patch('builtins.open', new_callable=mock_open)
    @patch('grobid_client.grobid_client.GrobidClient.post')
    def test_process_pdf_success(self, mock_post, mock_file):
        """Test process_pdf method with successful processing."""
        mock_response = Mock()
        mock_response.text = '<TEI>test content</TEI>'
        mock_post.return_value = (mock_response, 200)

        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

                result = client.process_pdf(
                    'processFulltextDocument',
                    '/test/document.pdf',
                    generateIDs=True,
                    consolidate_header=True,
                    consolidate_citations=False,
                    include_raw_citations=False,
                    include_raw_affiliations=False,
                    tei_coordinates=False,
                    segment_sentences=False
                )

                assert result[0] == '/test/document.pdf'
                assert result[1] == 200
                assert result[2] == '<TEI>test content</TEI>'

    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_process_pdf_file_not_found(self, mock_file):
        """Test process_pdf method with file not found error."""
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)
                client.logger = Mock()

                result = client.process_pdf(
                    'processFulltextDocument',
                    '/nonexistent/document.pdf',
                    generateIDs=False,
                    consolidate_header=False,
                    consolidate_citations=False,
                    include_raw_citations=False,
                    include_raw_affiliations=False,
                    tei_coordinates=False,
                    segment_sentences=False
                )

                assert result[1] == 400
                assert 'Failed to open file' in result[2]

    @patch('builtins.open', new_callable=mock_open, read_data='Reference 1\nReference 2\n')
    @patch('grobid_client.grobid_client.GrobidClient.post')
    def test_process_txt_success(self, mock_post, mock_file):
        """Test process_txt method with successful processing."""
        mock_response = Mock()
        mock_response.text = '<citations>parsed references</citations>'
        mock_post.return_value = (mock_response, 200)

        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                client = GrobidClient(check_server=False)

                result = client.process_txt(
                    'processCitationList',
                    '/test/references.txt',
                    generateIDs=False,
                    consolidate_header=False,
                    consolidate_citations=True,
                    include_raw_citations=True,
                    include_raw_affiliations=False,
                    tei_coordinates=False,
                    segment_sentences=False
                )

                assert result[0] == '/test/references.txt'
                assert result[1] == 200
                assert result[2] == '<citations>parsed references</citations>'

    @patch('grobid_client.grobid_client.GrobidClient.post')
    def test_process_pdf_server_busy_retry(self, mock_post):
        """Test process_pdf method with server busy (503) and retry."""
        # First call returns 503, second call returns 200
        mock_response_busy = Mock()
        mock_response_success = Mock()
        mock_response_success.text = '<TEI>success</TEI>'

        mock_post.side_effect = [
            (mock_response_busy, 503),
            (mock_response_success, 200)
        ]

        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                with patch('builtins.open', mock_open()):
                    with patch('time.sleep') as mock_sleep:
                        client = GrobidClient(check_server=False)
                        client.logger = Mock()

                        result = client.process_pdf(
                            'processFulltextDocument',
                            '/test/document.pdf',
                            generateIDs=False,
                            consolidate_header=False,
                            consolidate_citations=False,
                            include_raw_citations=False,
                            include_raw_affiliations=False,
                            tei_coordinates=False,
                            segment_sentences=False
                        )

                        # Should have called sleep due to 503 response
                        mock_sleep.assert_called_once()
                        assert result[1] == 200

    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('os.path.isfile', return_value=False)
    def test_process_batch(self, mock_isfile, mock_executor):
        """Test process_batch method."""
        # Mock the executor and futures
        mock_future = Mock()
        mock_future.result.return_value = ('/test/file.pdf', 200, '<TEI>content</TEI>')
        mock_executor_instance = Mock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor_instance.__enter__ = Mock(return_value=mock_executor_instance)
        mock_executor_instance.__exit__ = Mock(return_value=None)
        mock_executor.return_value = mock_executor_instance

        # Mock concurrent.futures.as_completed
        with patch('concurrent.futures.as_completed', return_value=[mock_future]):
            with patch('pathlib.Path'):
                with patch('builtins.open', mock_open()):
                    with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
                        with patch('grobid_client.grobid_client.GrobidClient._configure_logging'):
                            client = GrobidClient(check_server=False)
                            client.logger = Mock()

                            result = client.process_batch(
                                'processFulltextDocument',
                                ['/test/file.pdf'],
                                '/test',
                                '/output',
                                n=2,
                                generateIDs=False,
                                consolidate_header=False,
                                consolidate_citations=False,
                                include_raw_citations=False,
                                include_raw_affiliations=False,
                                tei_coordinates=False,
                                segment_sentences=False,
                                force=True,
                                verbose=False
                            )

                            assert result == (1, 0)  # One file processed, zero errors


class TestServerUnavailableException:
    """Test cases for ServerUnavailableException."""

    def test_exception_default_message(self):
        """Test exception with default message."""
        exception = ServerUnavailableException()
        assert str(exception) == "GROBID server is not available"
        assert exception.message == "GROBID server is not available"

    def test_exception_custom_message(self):
        """Test exception with custom message."""
        custom_message = "Custom server error message"
        exception = ServerUnavailableException(custom_message)
        assert str(exception) == custom_message
        assert exception.message == custom_message
