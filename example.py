from grobid_client.grobid_client import GrobidClient

if __name__ == "__main__":
    # Example 1: Using config file values (no constructor parameters)
    client = GrobidClient(config_path="./config.json")
    client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)
    
    # Example 2: Overriding config file with explicit server parameter
    # client = GrobidClient(grobid_server="https://lfoppiano-grobid.hf.space", config_path="./config.json")
    # client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)
    
    # Example 3: Using default values (no config file, no parameters)
    # client = GrobidClient()
    # client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)
