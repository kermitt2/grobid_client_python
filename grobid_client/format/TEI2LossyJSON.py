"""
    Convert the rich, unambiguous, standard, generic, extendable TEI XML format of GROBID and Pub2TEI into 
    something similar to CORD-19 degraded JSON format (let's call it a working format)

    Original version: https://github.com/howisonlab/softcite-dataset/blob/master/code/corpus/TEI2LossyJSON.py
"""
import argparse
import os
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict, Union, Optional, BinaryIO, Iterator

import dateparser
from bs4 import BeautifulSoup, NavigableString, Tag
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Basic configuration if not already configured by the application
    logging.basicConfig(level=logging.INFO)


class TEI2LossyJSONConverter:
    """Converter that can operate in two modes:
    - non-streaming (backwards-compatible): returns a full document dict for a single file
    - streaming: yields passages one by one to keep memory usage low when processing many files

    The class also provides utilities to process a directory of TEI files in parallel and in batches.
    """

    def __init__(self, validate_refs: bool = True):
        self.validate_refs = validate_refs

    def convert_tei_file(self, tei_file: Union[Path, BinaryIO], stream: bool = False):
        """Backward-compatible function. If stream=True returns a generator that yields passages (dicts).
        If stream=False returns the full document dict (same shape as original function).
        """
        # Load with BeautifulSoup but avoid building huge structures when streaming
        content = open(tei_file, 'r').read()
        soup = BeautifulSoup(content, 'xml')

        if soup.TEI is None:
            logger.warning("%s: The TEI file is not well-formed or empty. Skipping the file.", tei_file)
            return None if not stream else iter(())

        # Determine passage level early
        passage_level = "sentence" if len(soup.find_all("s")) > len(soup.find_all("p")) else "paragraph"

        if stream:
            # Use generator that yields passages as they are formatted
            return self._iter_passages_from_soup(soup, passage_level)
        else:
            # Build the full document (backward compatible)
            document = OrderedDict()
            document['level'] = passage_level

            biblio_structure = OrderedDict()
            document['biblio'] = biblio_structure

            text_structure = []
            document['body_text'] = text_structure
            figures_and_tables = []
            document['figures_and_tables'] = figures_and_tables

            # Populate header and body using the same traversal used by the generator
            for child in soup.TEI.children:
                if child.name == 'teiHeader':
                    # Header parsing mirrors original behavior
                    title_node = child.find("title", attrs={"type": "main", "level": "a"})
                    biblio_structure["title"] = title_node.text if title_node else ""
                    biblio_structure["authors"] = list(
                        filter(
                            lambda x: x.strip() != "",
                            [
                                " ".join(
                                    [
                                        author.find('forename').text if author.find('forename') is not None else "",
                                        author.find('surname').text if author.find('surname') is not None else ""
                                    ]
                                ) for author in child.find_all("author")
                            ]
                        )
                    )

                    doi_node = child.find("idno", type="DOI")
                    if doi_node:
                        biblio_structure['doi'] = doi_node.text

                    md5_node = child.find("idno", type="MD5")
                    if md5_node:
                        biblio_structure['hash'] = md5_node.text

                    pmc_idno = child.find("idno", type="PMC")
                    if pmc_idno:
                        biblio_structure['pmc'] = pmc_idno.text

                    pub_date = child.find("date", attrs={"type": "published"})
                    if pub_date:
                        iso_date = pub_date.attrs.get("when")
                        if iso_date:
                            biblio_structure["publication_date"] = iso_date
                            try:
                                year = dateparser.parse(iso_date).year
                                biblio_structure["publication_year"] = year
                            except Exception:
                                pass

                    publisherStmt = child.find("publicationStmt")
                    publisher_node = publisherStmt.find("publisher") if publisherStmt else None
                    if publisher_node:
                        biblio_structure["publisher"] = publisher_node.text

                    journal_node = child.find("title", attrs={"type": "main", "level": "j"})
                    if journal_node:
                        biblio_structure["journal"] = journal_node.text

                    journal_abbr_node = child.find("title", attrs={"type": "abbr", "level": "j"})
                    if journal_abbr_node:
                        biblio_structure["journal_abbr"] = journal_abbr_node.text

                    abstract_node = child.find("abstract")
                    if abstract_node:
                        abstract_paragraph_nodes = abstract_node.find_all("p")
                        if passage_level == "sentence":
                            biblio_structure["abstract"] = [
                                [
                                    {
                                        "id": sentence.get("xml:id") if sentence.has_attr("xml:id") else id,
                                        "text": sentence.text,
                                        "coords": [
                                            box_to_dict(coord.split(","))
                                            for coord in sentence['coords'].split(";")
                                        ] if sentence.has_attr("coords") else [],
                                        "refs": [
                                            {
                                                "type": ref["type"],
                                                "target": ref["target"] if "target" in ref.attrs else "",
                                                "text": ref.text
                                            }
                                            for ref in sentence.find_all("ref", type="bibr")
                                        ]
                                    }
                                    for id, sentence in enumerate(paragraph.find_all("s"))
                                ]
                                for paragraph in abstract_paragraph_nodes
                            ]
                        else:
                            biblio_structure["abstract"] = [
                                {
                                    "id": id,
                                    "text": paragraph.text,
                                    "coords": [
                                        box_to_dict(coord.split(","))
                                        for coord in paragraph['coords'].split(";")
                                    ] if paragraph.has_attr("coords") else [],
                                    "refs": [
                                        {
                                            "type": ref["type"],
                                            "target": ref["target"] if "target" in ref.attrs else "",
                                            "text": ref.text
                                        }
                                        for ref in paragraph.find_all("ref", type="bibr")
                                    ]
                                }
                                for id, paragraph in enumerate(abstract_paragraph_nodes)
                            ]

                elif child.name == 'text':
                    # Collect body_text using the generator to avoid duplicating logic
                    for passage in self._iter_passages_from_soup_for_text(child, passage_level):
                        text_structure.append(passage)

                    # Collect figures and tables (kept in memory as they should be relatively small)
                    figures_and_tables_xml = child.find_all("figure")
                    for item in figures_and_tables_xml:
                        item_id = item.attrs.get("xml:id") if item.has_attr("xml:id") else get_random_id()
                        desc = item.figDesc
                        head = item.head
                        label = item.label
                        if item.has_attr("type") and item.attrs["type"] == "table":
                            content = xml_table_to_markdown(item.table) if item.table else None
                            note = item.note
                            figures_and_tables.append(
                                {
                                    "id": item_id,
                                    "label": label.text if label else "",
                                    "head": head.text if head else "",
                                    "type": "table",
                                    "desc": desc.text if desc else "",
                                    "content": content,
                                    "note": note.text if note else "",
                                    "coords": [
                                        box_to_dict(coord.split(","))
                                        for coord in item['coords'].split(";")
                                    ] if item.has_attr("coords") else []
                                }
                            )
                        else:
                            graphic_coords = item.graphic.attrs['coords'] if item.graphic and item.graphic.has_attr(
                                "coords") else None
                            figures_and_tables.append(
                                {
                                    "id": item_id,
                                    "label": label.text if label else "",
                                    "head": head.text if head else "",
                                    "type": "figure",
                                    "desc": desc.text if desc else "",
                                    "note": item.note.text if item.note else "",
                                    "coords": [
                                        box_to_dict(coord.split(","))
                                        for coord in graphic_coords.split(";")
                                    ] if graphic_coords else []
                                }
                            )

            return document

    def _iter_passages_from_soup(self, soup: BeautifulSoup, passage_level: str) -> Iterator[Dict[str, Union[str, Dict[str, str]]]]:
        """Yield formatted passages discovered in the TEI soup. This yields the same structures
        as get_formatted_passage but one at a time to keep memory usage low."""
        for child in soup.TEI.children:
            if child.name == 'text':
                for passage in self._iter_passages_from_soup_for_text(child, passage_level):
                    yield passage

    def _iter_passages_from_soup_for_text(self, text_node: Tag, passage_level: str) -> Iterator[Dict[str, Union[str, Dict[str, str]]]]:
        head_paragraph = None
        div_nodes = text_node.find_all("div")
        for id_div, div in enumerate(div_nodes):
            head = div.find("head")
            p_nodes = div.find_all("p")
            head_section = None

            if head:
                if len(p_nodes) == 0:
                    head_paragraph = head.text
                else:
                    head_section = head.text

            for id_p, p in enumerate(p_nodes):
                paragraph_id = get_random_id(prefix="p_")
                if passage_level == "sentence":
                    for id_s, sentence in enumerate(p.find_all("s")):
                        struct = get_formatted_passage(head_paragraph, head_section, paragraph_id, sentence)
                        if self.validate_refs:
                            for ref in struct['refs']:
                                assert ref['offset_start'] < ref['offset_end']
                                assert struct['text'][ref['offset_start']:ref['offset_end']] == ref['text']
                        yield struct
                else:
                    struct = get_formatted_passage(head_paragraph, head_section, paragraph_id, p)
                    if self.validate_refs:
                        for ref in struct['refs']:
                            assert ref['offset_start'] < ref['offset_end']
                            assert struct['text'][ref['offset_start']:ref['offset_end']] == ref['text']
                    yield struct

    def process_directory(self, directory: Union[str, Path], pattern: str = "*.tei.xml", parallel: bool = True, workers: int = None) -> Iterator[Dict]:
        """Process a directory of TEI files and yield converted documents.
        When parallel=True this uses ProcessPoolExecutor to parallelize file-level conversion.
        Each yielded item is a dict with keys: 'path' and 'document' (document may be None on parse error).
        """
        directory = Path(directory)
        files = list(directory.rglob(pattern))
        if not parallel or len(files) <= 1:
            for f in files:
                yield {"path": f, "document": self.convert_tei_file(f, stream=False)}
            return

        # Use processes for CPU-bound parsing when many files are available
        workers = workers or min(32, (os.cpu_count() or 1))
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_convert_file_worker, str(f)): f for f in files}
            for fut in as_completed(futures):
                f = futures[fut]
                try:
                    doc = fut.result()
                except Exception:
                    logger.exception("Error processing %s", f)
                    doc = None
                yield {"path": f, "document": doc}


def _convert_file_worker(path: str):
    """Worker used by ProcessPoolExecutor. Imports inside function to avoid pickling issues."""
    from bs4 import BeautifulSoup
    import dateparser
    # Reuse existing top-level helpers from this module by importing here
    from grobid_client.format.TEI2LossyJSON import box_to_dict, get_random_id, get_formatted_passage, get_refs_with_offsets, xml_table_to_markdown
    content = open(path, 'r').read()
    soup = BeautifulSoup(content, 'xml')
    converter = TEI2LossyJSONConverter()
    return converter.convert_tei_file(path, stream=False)


def box_to_dict(coord_list):
    """Convert coordinate list to dictionary format."""
    if len(coord_list) >= 4:
        return {
            "x": float(coord_list[0]),
            "y": float(coord_list[1]),
            "width": float(coord_list[2]),
            "height": float(coord_list[3])
        }
    return {}


def get_random_id(prefix=""):
    """Generate a random ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def get_refs_with_offsets(element):
    """Extract references with their text offsets from an element."""
    refs = []
    text = element.get_text()
    
    for ref in element.find_all("ref", type="bibr"):
        ref_text = ref.get_text()
        if ref_text in text:
            start_offset = text.find(ref_text)
            end_offset = start_offset + len(ref_text)
            refs.append({
                "type": ref.get("type", ""),
                "target": ref.get("target", ""),
                "text": ref_text,
                "offset_start": start_offset,
                "offset_end": end_offset
            })
    
    return refs


def get_formatted_passage(head_paragraph, head_section, paragraph_id, element):
    """Format a passage (paragraph or sentence) with metadata and references."""
    text = element.get_text()
    refs = get_refs_with_offsets(element)
    
    passage = {
        "id": paragraph_id,
        "text": text,
        "coords": [
            box_to_dict(coord.split(","))
            for coord in element.get("coords", "").split(";")
        ] if element.has_attr("coords") else [],
        "refs": refs
    }
    
    if head_paragraph:
        passage["head_paragraph"] = head_paragraph
    if head_section:
        passage["head_section"] = head_section
    
    return passage


def xml_table_to_markdown(table_element):
    """Convert XML table to markdown format."""
    if not table_element:
        return None
    
    markdown_lines = []
    
    # Process table rows
    for row in table_element.find_all("row"):
        cells = []
        for cell in row.find_all("cell"):
            cell_text = cell.get_text().strip()
            cells.append(cell_text)
        
        if cells:
            markdown_lines.append("| " + " | ".join(cells) + " |")
    
    return "\n".join(markdown_lines) if markdown_lines else None


# Backwards compatible top-level function that uses the class
def convert_tei_file(tei_file: Union[Path, BinaryIO], stream: bool = False):
    converter = TEI2LossyJSONConverter()
    return converter.convert_tei_file(tei_file, stream=stream)
