'''
Recursively apply GROBID to the PDF present in a file tree via the grobid client and save the output XMLs in a cache without downloading them locally.
'''

import os
import re
import json
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import xml.etree.ElementTree as ET

grobid = __import__('grobid-client')

if __name__ == '__main__':
    
    client = grobid.grobid_client(config_path="./config.json")
    input_path = "/mnt/data/covid/data/"
    for root, _, _ in os.walk(input_path):
        client.process(root, root, 10, "processFulltextDocument", False, 1, 0, True, True, True, False, False)
        print(root)
        
    # client.cache contains a list of tuples containing the file name, path, and the XML output in a string form
    print(client.cache)

