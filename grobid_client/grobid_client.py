"""

Grobid Python Client

This version uses the standard ThreadPoolExecutor for parallelizing the
concurrent calls to the GROBID services.  Given the limits of
ThreadPoolExecutor (input stored in memory, blocking Executor.map until the 
whole input is acquired), it works with batches of PDF of a size indicated 
in the config.json file (default is 1000 entries). We are moving from first 
batch to the second one only when the first is entirely processed - which 
means it is slightly sub-optimal, but should scale better. Working without 
batch would mean acquiring a list of millions of files in directories and 
would require something scalable too (e.g. done in a separate thread), 
which is not implemented for the moment.

"""
import os
import json
import argparse
import time
import concurrent.futures
import ntpath
import requests
import pathlib
import logging
from typing import Tuple
import copy

from .client import ApiClient


class ServerUnavailableException(Exception):
    """Exception raised when GROBID server is not available or not responding."""

    def __init__(self, message="GROBID server is not available"):
        super().__init__(message)
        self.message = message


class GrobidClient(ApiClient):
    # Default configuration values
    DEFAULT_CONFIG = {
        'grobid_server': 'http://localhost:8070',
        'batch_size': 10,
        'sleep_time': 5,
        'timeout': 180,
        'coordinates': [
            "title",
            "persName",
            "affiliation",
            "orgName",
            "formula",
            "figure",
            "ref",
            "biblStruct",
            "head",
            "p",
            "s",
            "note"
        ],
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'console': True,
            'file': None,  # Disabled by default
            'max_file_size': '10MB',
            'backup_count': 3
        }
    }

    def __init__(
            self,
            grobid_server=None,
            batch_size=None,
            coordinates=None,
            sleep_time=None,
            timeout=None,
            config_path=None,
            check_server=True
    ):
        # Initialize config with defaults
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
    
        # Load config file (which may override current values)
        if config_path:
            self._load_config(config_path)
            
        # Constructor parameters take precedence over config file values
        # This ensures CLI arguments override config file values
        self._set_config_params({
            'grobid_server': grobid_server,
            'batch_size': batch_size,
            'coordinates': coordinates,
            'sleep_time': sleep_time,
            'timeout': timeout
        })

        # Configure logging based on config
        self._configure_logging()

        if check_server:
            self._test_server_connection()

    def _set_config_params(self, params):
        """Set configuration parameters, only if they are not None."""
        for key, value in params.items():
            if value is not None:
                self.config[key] = value

    def _handle_server_busy_retry(self, file_path, retry_func, *args, **kwargs):
        """Handle server busy (503) retry logic."""
        self.logger.warning(f"Server busy (503), retrying {file_path} after {self.config['sleep_time']} seconds")
        time.sleep(self.config["sleep_time"])
        return retry_func(*args, **kwargs)

    def _handle_request_error(self, file_path, error, error_type="Request"):
        """Handle request errors with consistent logging and return format."""
        self.logger.error(f"{error_type} failed for {file_path}: {str(error)}")
        return (file_path, 500, f"{error_type} failed: {str(error)}")

    def _handle_unexpected_error(self, file_path, error):
        """Handle unexpected errors with consistent logging and return format."""
        self.logger.error(f"Unexpected error processing {file_path}: {str(error)}")
        return (file_path, 500, f"Unexpected error: {str(error)}")

    def _configure_logging(self):
        """Configure logging based on the configuration settings."""
        # Get logging config with defaults
        log_config = self.config.get('logging', {})

        # Parse log level
        log_level_str = log_config.get('level', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Parse log format
        log_format = log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Configure the logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        # Clear any existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Console handler
        if log_config.get('console', True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        log_file = log_config.get('file')
        if log_file:
            try:
                # Parse file size (support formats like "10MB", "1GB", etc.)
                max_bytes = self._parse_file_size(log_config.get('max_file_size', '10MB'))
                backup_count = log_config.get('backup_count', 3)

                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

                self.logger.debug(
                    f"File logging configured: {log_file} (max size: {max_bytes}, backups: {backup_count})")
            except Exception as e:
                # Fallback to basic file handler if rotating handler fails
                try:
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(log_level)
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)
                    self.logger.warning(f"Using basic file handler due to error with rotating handler: {e}")
                except Exception as file_error:
                    self.logger.warning(f"Could not configure file logging: {file_error}")

        self.logger.info(
            f"Logging configured - Level: {log_level_str}, Console: {log_config.get('console', True)}, File: {log_file or 'disabled'}")

    def _parse_file_size(self, size_str):
        """Parse file size string like '10MB', '1GB' to bytes."""
        size_str = str(size_str).upper().strip()

        # Extract number and unit
        import re
        match = re.match(r'(\d+(?:\.\d+)?)\s*([KMGT]?B?)', size_str)
        if not match:
            return 10 * 1024 * 1024  # Default 10MB

        number = float(match.group(1))
        unit = match.group(2)

        # Convert to bytes
        multipliers = {
            '': 1,
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }

        return int(number * multipliers.get(unit, 1))

    def _load_config(self, path="./config.json"):
        """
        Load and merge configuration from a JSON file with default values.
        If the file doesn't exist, keep the default values.

        Args:
            path (str): Path to the JSON configuration file

        Raises:
            FileNotFoundError: If the config file is not found
            json.JSONDecodeError: If the config file contains invalid JSON
            Exception: For other file reading errors
        """
        # Create a temporary logger for configuration loading since main logger isn't configured yet
        temp_logger = logging.getLogger(f"{__name__}.config_loader")
        if not temp_logger.handlers:
            temp_handler = logging.StreamHandler()
            temp_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            temp_logger.addHandler(temp_handler)
            temp_logger.setLevel(logging.INFO)

        try:
            temp_logger.info(f"Loading configuration file from {path}")
            with open(path, 'r') as config_file:
                config_json = config_file.read()
                # Update the default config with values from the file
                file_config = json.loads(config_json)
                self.config.update(file_config)
                temp_logger.info("Configuration file loaded successfully")
        except FileNotFoundError as e:
            # If config file doesn't exist, keep using default values
            error_msg = f"The specified config file {path} was not found. Check the path or leave it blank to use the default configuration."
            temp_logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e
        except json.JSONDecodeError as e:
            # If config exists, but it's invalid, we raise an exception
            error_msg = f"Could not parse config file at {path}: {str(e)}"
            temp_logger.error(error_msg)
            raise json.JSONDecodeError(error_msg, e.doc, e.pos) from e
        except Exception as e:
            error_msg = f"Error reading config file at {path}: {str(e)}"
            temp_logger.error(error_msg)
            raise Exception(error_msg) from e

    def _test_server_connection(self) -> Tuple[bool, int]:
        """Test if the server is up and running.

        Returns:
            tuple: (is_available, status_code)

        Raises:
            ServerUnavailableException: If server is not reachable
        """
        the_url = self.get_server_url("isalive")
        try:
            r = requests.get(the_url, timeout=10)
            status = r.status_code

            if status != 200:
                error_msg = f"GROBID server {self.config['grobid_server']} does not appear up and running (status: {status})"
                self.logger.error(error_msg)
                return False, status
            else:
                self.logger.info(f"GROBID server {self.config['grobid_server']} is up and running")
                return True, status

        except requests.exceptions.RequestException as e:
            error_msg = f"GROBID server {self.config['grobid_server']} does not appear up and running, connection failed: {str(e)}"
            self.logger.error(error_msg)
            raise ServerUnavailableException(error_msg) from e

    def _output_file_name(self, input_file, input_path, output):
        # we use ntpath here to be sure it will work on Windows too
        if output is not None:
            input_file_name = str(os.path.relpath(os.path.abspath(input_file), input_path))
            filename = os.path.join(
                output, os.path.splitext(input_file_name)[0] + ".grobid.tei.xml"
            )
        else:
            input_file_name = ntpath.basename(input_file)
            filename = os.path.join(
                ntpath.dirname(input_file),
                os.path.splitext(input_file_name)[0] + ".grobid.tei.xml",
            )

        return filename

    def ping(self) -> Tuple[bool, int]:
        """
        Check the Grobid service. Returns True if the service is up.
        In addition, returns also the status code.
        """
        return self._test_server_connection()

    def process(
            self,
            service,
            input_path,
            output=None,
            n=10,
            generateIDs=False,
            consolidate_header=True,
            consolidate_citations=False,
            include_raw_citations=False,
            include_raw_affiliations=False,
            tei_coordinates=False,
            segment_sentences=False,
            force=True,
            verbose=False,
            flavor=None
    ):
        batch_size_pdf = self.config["batch_size"]

        # First pass: count all eligible files
        all_input_files = []
        for (dirpath, dirnames, filenames) in os.walk(input_path):
            for filename in filenames:
                if filename.endswith(".pdf") or filename.endswith(".PDF") or \
                        (service == 'processCitationList' and (
                                filename.endswith(".txt") or filename.endswith(".TXT"))) or \
                        (service == 'processCitationPatentST36' and (
                                filename.endswith(".xml") or filename.endswith(".XML"))):
                    full_path = os.sep.join([dirpath, filename])
                    all_input_files.append(full_path)

        # Log total files found
        total_files = len(all_input_files)
        if total_files == 0:
            self.logger.warning(f"No eligible files found in {input_path}")
            return

        self.logger.info(f"Found {total_files} file(s) to process")

        # Counter for actually processed files
        processed_files_count = 0
        errors_files_count = 0
        input_files = []

        for input_file in all_input_files:
            # Extract just the filename for verbose logging
            filename = os.path.basename(input_file)

            if verbose:
                try:
                    self.logger.info(f"Found file: {filename}")
                except UnicodeEncodeError:
                    # may happen on linux see https://stackoverflow.com/questions/27366479/python-3-os-walk-file-paths-unicodeencodeerror-utf-8-codec-cant-encode-s
                    self.logger.warning(f"Could not log filename due to encoding issues")

            input_files.append(input_file)

            if len(input_files) == batch_size_pdf:
                batch_processed, batch_errors = self.process_batch(
                    service,
                    input_files,
                    input_path,
                    output,
                    n,
                    generateIDs,
                    consolidate_header,
                    consolidate_citations,
                    include_raw_citations,
                    include_raw_affiliations,
                    tei_coordinates,
                    segment_sentences,
                    force,
                    verbose,
                    flavor
                )
                processed_files_count += batch_processed
                errors_files_count += batch_errors
                input_files = []

        # last batch
        if len(input_files) > 0:
            batch_processed, batch_errors = self.process_batch(
                service,
                input_files,
                input_path,
                output,
                n,
                generateIDs,
                consolidate_header,
                consolidate_citations,
                include_raw_citations,
                include_raw_affiliations,
                tei_coordinates,
                segment_sentences,
                force,
                verbose,
            )
            processed_files_count += batch_processed
            errors_files_count += batch_errors

        # Log final statistics
        self.logger.info(f"Processing completed: {processed_files_count} out of {total_files} files processed")
        self.logger.info(f"Errors: {errors_files_count} out of {total_files} files processed")

    def process_batch(
            self,
            service,
            input_files,
            input_path,
            output,
            n,
            generateIDs,
            consolidate_header,
            consolidate_citations,
            include_raw_citations,
            include_raw_affiliations,
            tei_coordinates,
            segment_sentences,
            force,
            verbose=False,
            flavor=None
    ):
        if verbose:
            self.logger.info(f"{len(input_files)} files to process in current batch")

        processed_count = 0
        error_count = 0

        # we use ThreadPoolExecutor and not ProcessPoolExecutor because it is an I/O intensive process
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
            # with concurrent.futures.ProcessPoolExecutor(max_workers=n) as executor:
            results = []
            for input_file in input_files:
                # check if TEI file is already produced
                filename = self._output_file_name(input_file, input_path, output)
                if not force and os.path.isfile(filename):
                    self.logger.info(
                        f"{filename} already exists, skipping... (use --force to reprocess pdf input files)")
                    continue

                selected_process = self.process_pdf
                if service == 'processCitationList':
                    selected_process = self.process_txt

                if verbose:
                    self.logger.info(f"Adding {input_file} to the queue")

                r = executor.submit(
                    selected_process,
                    service,
                    input_file,
                    generateIDs,
                    consolidate_header,
                    consolidate_citations,
                    include_raw_citations,
                    include_raw_affiliations,
                    tei_coordinates,
                    segment_sentences,
                    flavor,
                    -1,
                    -1)

                results.append(r)

        for r in concurrent.futures.as_completed(results):
            input_file, status, text = r.result()
            filename = self._output_file_name(input_file, input_path, output)

            if status != 200 or text is None:
                self.logger.error(f"Processing of {input_file} failed with error {status}: {text}")
                error_count += 1
                # writing error file with suffixed error code
                try:
                    pathlib.Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)
                    error_filename = filename.replace(".grobid.tei.xml", f"_{status}.txt")
                    with open(error_filename, 'w', encoding='utf8') as error_file:
                        if text is not None:
                            error_file.write(text)
                        else:
                            error_file.write("")
                    self.logger.info(f"Error details written to {error_filename}")
                except OSError as e:
                    self.logger.error(f"Failed to write error file {filename}: {str(e)}")
            else:
                processed_count += 1
                # writing TEI file
                try:
                    pathlib.Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)
                    with open(filename, 'w', encoding='utf8') as tei_file:
                        tei_file.write(text)
                    self.logger.debug(f"Successfully wrote TEI file: {filename}")
                except OSError as e:
                    self.logger.error(f"Failed to write TEI XML file {filename}: {str(e)}")

        return processed_count, error_count

    def process_pdf(
            self,
            service,
            pdf_file,
            generateIDs,
            consolidate_header,
            consolidate_citations,
            include_raw_citations,
            include_raw_affiliations,
            tei_coordinates,
            segment_sentences,
            flavor=None,
            start=-1,
            end=-1
    ):
        pdf_handle = None
        try:
            pdf_handle = open(pdf_file, "rb")
            
            files = {
                "input": (
                    pdf_file,
                    pdf_handle,
                    "application/pdf",
                    {"Expires": "0"},
                )
            }

            the_url = self.get_server_url(service)

            # set the GROBID parameters
            the_data = {}
            if generateIDs:
                the_data["generateIDs"] = "1"
            if consolidate_header:
                the_data["consolidateHeader"] = "1"
            if consolidate_citations:
                the_data["consolidateCitations"] = "1"
            if include_raw_citations:
                the_data["includeRawCitations"] = "1"
            if include_raw_affiliations:
                the_data["includeRawAffiliations"] = "1"
            if tei_coordinates:
                the_data["teiCoordinates"] = self.config["coordinates"]
            if segment_sentences:
                the_data["segmentSentences"] = "1"
            if flavor:
                the_data["flavor"] = flavor
            if start and start > 0:
                the_data["start"] = str(start)
            if end and end > 0:
                the_data["end"] = str(end)

            res, status = self.post(
                url=the_url, files=files, data=the_data, headers={"Accept": "text/plain"},
                timeout=self.config['timeout']
            )

            if status == 503:
                return self._handle_server_busy_retry(
                    pdf_file,
                    self.process_pdf,
                    service,
                    pdf_file,
                    generateIDs,
                    consolidate_header,
                    consolidate_citations,
                    include_raw_citations,
                    include_raw_affiliations,
                    tei_coordinates,
                    segment_sentences,
                    flavor,
                    start,
                    end
                )

            return (pdf_file, status, res.text)
        
        except IOError as e:
            self.logger.error(f"Failed to open PDF file {pdf_file}: {str(e)}")
            return (pdf_file, 400, f"Failed to open file: {str(e)}")
        except requests.exceptions.ReadTimeout as e:
            self.logger.error(f"Request timeout for {pdf_file}: {str(e)}")
            return (pdf_file, 408, f"Request timeout: {str(e)}")
        except requests.exceptions.RequestException as e:
            return self._handle_request_error(pdf_file, e)
        except Exception as e:
            return self._handle_unexpected_error(pdf_file, e)
        finally:
            if pdf_handle:
                pdf_handle.close()

    def get_server_url(self, service):
        return self.config['grobid_server'] + "/api/" + service

    def process_txt(
            self,
            service,
            txt_file,
            generateIDs,
            consolidate_header,
            consolidate_citations,
            include_raw_citations,
            include_raw_affiliations,
            tei_coordinates,
            segment_sentences
    ):
        # create request based on file content
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                references = [line.rstrip() for line in f]
        except IOError as e:
            self.logger.error(f"Failed to read text file {txt_file}: {str(e)}")
            return (txt_file, 500, f"Failed to read file: {str(e)}")
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error reading {txt_file}: {str(e)}")
            return (txt_file, 500, f"Unicode decode error: {str(e)}")

        the_url = self.get_server_url(service)

        # set the GROBID parameters
        the_data = {}
        if consolidate_citations:
            the_data["consolidateCitations"] = "1"
        if include_raw_citations:
            the_data["includeRawCitations"] = "1"
        the_data["citations"] = references

        try:
            res, status = self.post(
                url=the_url, data=the_data, headers={"Accept": "application/xml"}
            )

            if status == 503:
                return self._handle_server_busy_retry(
                    txt_file,
                    self.process_txt,
                    service,
                    txt_file,
                    generateIDs,
                    consolidate_header,
                    consolidate_citations,
                    include_raw_citations,
                    include_raw_affiliations,
                    tei_coordinates,
                    segment_sentences
                )
        except requests.exceptions.RequestException as e:
            return self._handle_request_error(txt_file, e)
        except Exception as e:
            return self._handle_unexpected_error(txt_file, e)

        return (txt_file, status, res.text)


def main():
    # Basic logging setup for initialization only
    # The actual logging configuration will be done by GrobidClient based on config.json
    temp_logger = logging.getLogger(__name__)
    temp_handler = logging.StreamHandler()
    temp_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    temp_logger.addHandler(temp_handler)
    temp_logger.setLevel(logging.INFO)

    valid_services = [
        "processFulltextDocument",
        "processHeaderDocument",
        "processReferences",
        "processCitationList",
        "processCitationPatentST36",
        "processCitationPatentPDF"
    ]

    parser = argparse.ArgumentParser(description="Client for GROBID services")
    parser.add_argument(
        "service",
        choices=valid_services,
        help="Grobid service to be called.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="path to the directory containing files to process: PDF or .txt (for processCitationList only, one reference per line), or .xml for patents in ST36"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="path to the directory where to put the results (optional)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="path to the config file (optional)",
    )
    parser.add_argument(
        "--n",
        default=10,
        help="concurrency for service usage"
    )
    parser.add_argument(
        "--generateIDs",
        action="store_true",
        help="generate random xml:id to textual XML elements of the result files",
    )
    parser.add_argument(
        "--consolidate_header",
        action="store_true",
        help="call GROBID with consolidation of the metadata extracted from the header",
    )
    parser.add_argument(
        "--consolidate_citations",
        action="store_true",
        help="call GROBID with consolidation of the extracted bibliographical references",
    )
    parser.add_argument(
        "--include_raw_citations",
        action="store_true",
        help="call GROBID requesting the extraction of raw citations",
    )
    parser.add_argument(
        "--include_raw_affiliations",
        action="store_true",
        help="call GROBID requestiong the extraciton of raw affiliations",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="force re-processing pdf input files when tei output files already exist",
    )
    parser.add_argument(
        "--teiCoordinates",
        action="store_true",
        help="add the original PDF coordinates (bounding boxes) to the extracted elements",
    )
    parser.add_argument(
        "--segmentSentences",
        action="store_true",
        help="segment sentences in the text content of the document with additional <s> elements",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print information about processed files in the console",
    )

    parser.add_argument(
        "--flavor",
        default=None,
        help="Define the flavor to be used for the fulltext extraction",
    )
    parser.add_argument(
        "--server",
        default=None,
        help="GROBID server URL override of the config file. If config not provided, default is http://localhost:8070",
    )

    args = parser.parse_args()

    input_path = args.input
    config_path = args.config
    output_path = args.output
    flavor = args.flavor

    # Initialize n with default value
    n = 10
    if args.n is not None:
        try:
            n = int(args.n)
        except ValueError:
            temp_logger.warning(f"Invalid concurrency parameter n: {args.n}. Using default value n = 10")

    # Initialize GrobidClient which will configure logging based on config.json
    try:
        # Only pass grobid_server if it was explicitly provided (not the default)
        client_kwargs = {'config_path': config_path}
        if args.server is not None:  # Only override if user specified a different server
            client_kwargs['grobid_server'] = args.server
            
        client = GrobidClient(**client_kwargs)
        # Now use the client's logger for all subsequent logging
        logger = client.logger
    except ServerUnavailableException as e:
        temp_logger.error(f"Server unavailable: {str(e)}")
        exit(1)
    except Exception as e:
        temp_logger.error(f"Failed to initialize GrobidClient: {str(e)}")
        exit(1)

    # if output path does not exist, we create it
    if output_path is not None and not os.path.isdir(output_path):
        try:
            logger.info(f"Output directory does not exist but will be created: {output_path}")
            os.makedirs(output_path)
            logger.info(f"Successfully created the directory {output_path}")
        except OSError as e:
            logger.error(f"Creation of the directory {output_path} failed: {str(e)}")
            exit(1)

    service = args.service
    generateIDs = args.generateIDs
    consolidate_header = args.consolidate_header
    consolidate_citations = args.consolidate_citations
    include_raw_citations = args.include_raw_citations
    include_raw_affiliations = args.include_raw_affiliations
    force = args.force
    tei_coordinates = args.teiCoordinates
    segment_sentences = args.segmentSentences
    verbose = args.verbose

    if service is None or service not in valid_services:
        logger.error(f"Missing or invalid service '{service}', must be one of {valid_services}")
        exit(1)

    start_time = time.time()

    try:
        client.process(
            service,
            input_path,
            output=output_path,
            n=n,
            generateIDs=generateIDs,
            consolidate_header=consolidate_header,
            consolidate_citations=consolidate_citations,
            include_raw_citations=include_raw_citations,
            include_raw_affiliations=include_raw_affiliations,
            tei_coordinates=tei_coordinates,
            segment_sentences=segment_sentences,
            force=force,
            verbose=verbose,
            flavor=flavor
        )
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        exit(1)

    runtime = round(time.time() - start_time, 3)
    logger.info(f"Processing completed in {runtime} seconds")


if __name__ == "__main__":
    main()
