from grobid_client.grobid_client import GrobidClient

if __name__ == "__main__":
    # Example with default localhost server
    client = GrobidClient(config_path="./config.json")
    client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)
    
    # Example with custom server (uncomment to use)
    # client = GrobidClient(grobid_server="https://lfoppiano-grobid.hf.space", config_path="./config.json")
    # client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)
