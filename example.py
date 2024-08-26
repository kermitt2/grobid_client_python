from grobid_client.grobid_client import GrobidClient

if __name__ == "__main__":
    client = GrobidClient(config_path="./config.json")
    client.process("processFulltextDocument", "./resources/test_pdf", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)

    texts = [ "P & W Trading, 63 avenue de l'Europe F-77184 Emerainville FR", 
              "1-5: Jacob Johan Würtzen, Nyhavn 3, 1051 København, Denmark",
              "John Smith, 63 avenue de l'Europe F-77184 Emerainville FR; Robert Moore, 63 avenue de l'Europe F-77184 Emerainville FR"]

    _, status, result = client.process_list("processNameAddressList", texts)
    print(result)

    _, status, result = client.process_list("processNameAddressList", texts, response_type="application/json")
    print(result)
