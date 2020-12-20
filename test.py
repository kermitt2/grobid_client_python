'''
Recursively apply GROBID to the PDF present in a file tree via the grobid client.
'''

import grobid_client as grobid

if __name__ == "__main__":

    client = grobid.grobid_client(config_path="./config.json")
    client.process("processFulltextDocument", "./resources/test", consolidate_citations=True, teiCoordinates=True, force=True)
