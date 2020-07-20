# Simple python client for GROBID REST services

This Python client is used to process a single PDF document by the  [GROBID](https://github.com/kermitt2/grobid) service. Results are returned in an XML format.

## Build and run

You need first to install and start the *grobid* service, latest stable version, see the [documentation](http://grobid.readthedocs.io/).  The default server host is `localhost` and port is `8081`.  The `GrobidClient` can be configure via host and port. 

## Requirements

This client has been developed and tested with Python 3.7.

## Install

```
pip install pygrobid
```

## Usage and options

```

You can take a quick test via `python tests.py pdf_file -h host -p port`

In your code: 

```  
from pygrobid import GrobidClient

client = GrobidClient(host, port)
rsp = client.serve(service_name, pdf_file)
rsp = client.serve(service_name, pdf_file, consolidate_header=1)

``` 

## Acknoledgement  

This project is based on [grobid-python-client](https://github.com/kermitt2/grobid-client-python) by Patrice Lopez (<patrice.lopez@science-miner.com>)
