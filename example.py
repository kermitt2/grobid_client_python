from grobid_client.grobid_client import GrobidClient

if __name__ == "__main__":
    client = GrobidClient(config_path="./config.json")
    client.process("processFulltextDocument", "./resources/test", output="./resources/test_out/", consolidate_citations=True, teiCoordinates=True, force=True)
