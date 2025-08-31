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
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
        assert client.config['batch_size'] == 1000
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
                    mock_batch.return_value = 2
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

                            assert result == 1  # One file processed


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


# ============================================================================
# CONFIGURATION SCENARIOS TEST CLASS
# ============================================================================


class TestConfigurationScenarios:
    """Test various configuration scenarios using test configuration files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_files = []

    def teardown_method(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except OSError:
                pass

    def create_temp_config(self, config_data):
        """Create a temporary configuration file."""
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(json.dumps(config_data))
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def test_valid_configuration(self):
        """Test with valid configuration file."""
        config_data = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 1000,
            'coordinates': ["persName", "figure", "ref"],
            'sleep_time': 5,
            'timeout': 180,
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                assert client.config['grobid_server'] == "http://localhost:8070"
                assert client.config['batch_size'] == 1000
                assert client.config['timeout'] == 180
                assert client.config['sleep_time'] == 5
                assert len(client.config['coordinates']) == 3
                assert client.config['logging']['level'] == "INFO"

    def test_custom_server_configuration(self):
        """Test with custom server configuration."""
        config_data = {
            'grobid_server': 'http://custom-server:9090',
            'batch_size': 500,
            'coordinates': ["title", "figure"],
            'sleep_time': 10,
            'timeout': 300,
            'logging': {
                'level': 'DEBUG',
                'format': '%(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                assert client.config['grobid_server'] == "http://custom-server:9090"
                assert client.config['batch_size'] == 500
                assert client.config['timeout'] == 300
                assert client.config['sleep_time'] == 10
                assert client.config['coordinates'] == ["title", "figure"]
                assert client.config['logging']['level'] == "DEBUG"

    def test_file_logging_configuration(self):
        """Test with file logging configuration."""
        config_data = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 1000,
            'logging': {
                'level': 'WARNING',
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'console': False,
                'file': '/tmp/grobid_test.log',
                'max_file_size': '5MB',
                'backup_count': 2
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.handlers.RotatingFileHandler'):
                    # Mock the logger to avoid interference with the temporary logger
                    mock_logger = Mock()
                    mock_get_logger.return_value = mock_logger
                    client = GrobidClient(config_path=config_file, check_server=False)
                    
                    assert client.config['logging']['level'] == "WARNING"
                    assert client.config['logging']['console'] is False
                    assert client.config['logging']['file'] == "/tmp/grobid_test.log"
                    assert client.config['logging']['max_file_size'] == "5MB"
                    assert client.config['logging']['backup_count'] == 2

    def test_minimal_configuration(self):
        """Test with minimal configuration (only required fields)."""
        config_data = {
            'grobid_server': 'http://localhost:8070'
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should use default values for missing fields
                assert client.config['grobid_server'] == "http://localhost:8070"
                assert client.config['batch_size'] == 1000  # Default
                assert client.config['timeout'] == 180  # Default
                assert client.config['sleep_time'] == 5  # Default

    def test_invalid_configuration(self):
        """Test with invalid configuration (wrong data types)."""
        config_data = {
            'grobid_server': 123,  # Should be string
            'batch_size': "not_a_number",  # Should be int
            'timeout': "invalid_timeout",  # Should be int
            'sleep_time': None,  # Should be int
            'coordinates': "not_a_list",  # Should be list
            'logging': "not_a_dict"  # Should be dict
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should accept any values (validation happens elsewhere)
                assert client.config['grobid_server'] == 123
                assert client.config['batch_size'] == "not_a_number"
                assert client.config['timeout'] == "invalid_timeout"
                assert client.config['sleep_time'] is None
                assert client.config['coordinates'] == "not_a_list"
                assert client.config['logging'] == "not_a_dict"

    def test_none_values_configuration(self):
        """Test with None values in configuration."""
        config_data = {
            'grobid_server': None,
            'batch_size': None,
            'timeout': None,
            'sleep_time': None,
            'coordinates': None,
            'logging': None
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should accept None values
                assert client.config['grobid_server'] is None
                assert client.config['batch_size'] is None
                assert client.config['timeout'] is None
                assert client.config['sleep_time'] is None
                assert client.config['coordinates'] is None
                assert client.config['logging'] is None

    def test_empty_values_configuration(self):
        """Test with empty values in configuration."""
        config_data = {
            'grobid_server': '',
            'batch_size': 0,
            'timeout': 0,
            'sleep_time': 0,
            'coordinates': [],
            'logging': {}
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should accept empty values
                assert client.config['grobid_server'] == ''
                assert client.config['batch_size'] == 0
                assert client.config['timeout'] == 0
                assert client.config['sleep_time'] == 0
                assert client.config['coordinates'] == []
                assert client.config['logging'] == {}

    def test_extreme_values_configuration(self):
        """Test with extreme values in configuration."""
        config_data = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 999999999,
            'timeout': 999999999,
            'sleep_time': 999999999,
            'coordinates': ["a" * 1000],  # Very long string
            'logging': {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should accept extreme values
                assert client.config['batch_size'] == 999999999
                assert client.config['timeout'] == 999999999
                assert client.config['sleep_time'] == 999999999
                assert client.config['coordinates'] == ["a" * 1000]

    def test_unicode_configuration(self):
        """Test with Unicode characters in configuration."""
        config_data = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 1000,
            'coordinates': ["用户名", "密码", "文档"],
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should handle Unicode characters
                assert client.config['coordinates'] == ["用户名", "密码", "文档"]

    def test_special_characters_configuration(self):
        """Test with special characters in configuration."""
        config_data = {
            'grobid_server': 'http://localhost:8070',
            'batch_size': 1000,
            'coordinates': ["test@example.com", "file/path", "user-name"],
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should handle special characters
                assert client.config['coordinates'] == ["test@example.com", "file/path", "user-name"]

    def test_constructor_override_configuration(self):
        """Test that constructor parameters override config file values."""
        config_data = {
            'grobid_server': 'http://config-server:8080',
            'batch_size': 1000,
            'timeout': 180,
            'sleep_time': 5,
            'coordinates': ["config_coord"],
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'console': True,
                'file': None
            }
        }
        config_file = self.create_temp_config(config_data)
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(
                    config_path=config_file,
                    grobid_server="http://constructor-server:9090",
                    batch_size=500,
                    timeout=300,
                    sleep_time=10,
                    coordinates=["constructor_coord"],
                    check_server=False
                )
                
                # Constructor parameters should override config file
                assert client.config['grobid_server'] == "http://constructor-server:9090"
                assert client.config['batch_size'] == 500
                assert client.config['timeout'] == 300
                assert client.config['sleep_time'] == 10
                assert client.config['coordinates'] == ["constructor_coord"]

    def test_missing_config_file(self):
        """Test behavior when config file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            GrobidClient(config_path="/nonexistent/config.json", check_server=False)
        
        assert "was not found" in str(exc_info.value)

    def test_invalid_json_config_file(self):
        """Test behavior with invalid JSON in config file."""
        # Create a temporary file with invalid JSON
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write('invalid json content')
        temp_file.close()
        self.temp_files.append(temp_file.name)
        
        with pytest.raises(json.JSONDecodeError):
            GrobidClient(config_path=temp_file.name, check_server=False)

    def test_empty_config_file(self):
        """Test behavior with empty config file."""
        config_file = self.create_temp_config({})
        
        with patch('grobid_client.grobid_client.GrobidClient._test_server_connection'):
            with patch('logging.getLogger') as mock_get_logger:
                # Mock the logger to avoid interference with the temporary logger
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                client = GrobidClient(config_path=config_file, check_server=False)
                
                # Should use default values
                assert client.config['grobid_server'] == "http://localhost:8070"
                assert client.config['batch_size'] == 1000
                assert client.config['timeout'] == 180
                assert client.config['sleep_time'] == 5
