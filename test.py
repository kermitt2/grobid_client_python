'''
Test if GrobidClient works
'''

import argparse
from grobid import GrobidClient

parser = argparse.ArgumentParser(
    description='Obtain host and port of Grobid Server')

parser.add_argument('pdf', help='PDF files to test')
parser.add_argument('-s', '--host', default="localhost",
                    help='Server Host')
parser.add_argument('-p', '--port', default="8080",
                    help='Server Port')
parser.add_argument('-c', '--consolidate', default="0",
                    help='Consolidate or not')


if __name__ == "__main__":
    args = parser.parse_args()
    client = GrobidClient(args.host, args.port)

    # /processHeaderDocument without consolidate
    rsp = client.serve("processHeaderDocument", args.pdf,
                       consolidate_header=args.consolidate)
    if args.consolidate == 1:
        result = "with"
    else:
        result = "WITHOUT"
    msg = f"process header Document {result} consolidate"
    print(msg, len(rsp))
