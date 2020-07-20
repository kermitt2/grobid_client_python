from client import ApiClient
import requests


class GrobidClient(ApiClient):

    def __init__(self, host="localhost", port="8080"):
        self.host = host
        self.port = port
        self.url = f"{self.host}:{self.port}"

    def test_alive(self):
        url = f"{self.url}/api/isalive"
        rsp = requests.get(url)
        return rsp.status == 200

    def serve(self, service, pdf_file, generateIDs=1, consolidate_header="0",
              consolidate_citations=0,
              teiCoordinates=["persName", "figure", "ref", "biblStruct",
                              "formula"]
              ):

        files = {'input': open(pdf_file, 'rb')}

        url = f"{self.url}/api/{service}"

        # set the GROBID parameters
        the_data = {
            "generateIDs": generateIDs,
            "consolidateHeader": consolidate_header,
            "consolidateCitations": consolidate_citations,
        }

        res, status = self.post(
            url=url,
            files=files,
            data=the_data,
            headers={'Accept': 'text/plain'}
        )

        if status == 200:
            return res.text

        raise status
