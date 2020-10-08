'''
Recursively apply GROBID to the PDF present in a file tree via the grobid client.
'''

import os
grobid = __import__('grobid-client')

if __name__ == "__main__":

    client = grobid.grobid_client(config_path="./config.json")
    input_path = "/mnt/data/covid/data/"
    for root, _, _ in os.walk(input_path):
        client.process(root, root, 10, "processFulltextDocument", False, 1, 0, True, True, True, False)
        print(root)
                