# -*- coding: utf-8 -*-
"""
    #-------------------------------------------------------------------------------
    # Name:        PARSE ARXIV XML
    # Purpose:     Parses the XML metadata file from ArXiv, and inserts some
    #              of the fields into Solr for each record.
    #
    # Author:      Ashwath Sampath
    #
    # Created:     20-06-2018
    # Copyright:   (c) Ashwath Sampath 2018
    #-------------------------------------------------------------------------------

"""
from collections import defaultdict
from lxml import etree
import pysolr
# Parse the Arxiv xml file
def get_xml_root():
    """ Gets the root of the arxiv xml tree and returns it."""
    xml_filepath = '/home/ashwath/arxiv-cs-all-until201712031.xml'
#    xml_filepath = 'D:\\Coursework\\HiWi\\arxiv-cs-all-until201712031.xml'
    doc = etree.parse(xml_filepath)
    root = doc.getroot()
    return root

def parse_xml_insert_into_solr(root):
    """ Function which parses the arxiv xml, and inserts some of the metadata
    into an index in Apache Solr."""
    # Set the 2 namespaces which are used in the xml file: Open archive,
    # and Dublin Core.
    namespace = {'dc': 'http://purl.org/dc/elements/1.1/',
                 'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'}
    # NOTE: this is the fully qualified version of descending through the ns
    # for m in root.find('./record/metadata/'
    # '{http://www.openarchives.org/OAI/2.0/oai_dc/}dc/'
    #'[{http://purl.org/dc/elements/1.1/}identifier=
    # "http://arxiv.org/abs/0704.0002"]'):
    
    # Descend down to the metadata node in all the records: it has all the
    # interesting fields as its children.
    metadata_xpath = './record/metadata/'
    # metadata is a list, but len(metadata) = len(root) = 155308.
    # Each member of metadata, metadata[i] is of type lxml.etree._Element node,
    # the same as root. So we can loop through it to get its children.
    metadata = root.findall(metadata_xpath, namespaces=namespace)
    #print(len(metadata))
    # Get the index of the first character after the dc prefix, it's going to
    # be the same for all children. {http://purl.org/dc/elements/1.1/}title
    # Get the tag of the first record's title, and run find on that. Ans. 34
    tag_with_prefix = metadata[0][0].tag # for first child
    start_index = tag_with_prefix.find('}') + 1 # 34
    list_for_solr = []
    for metadata_element in metadata:
        solr_record = defaultdict(list)
        for child in metadata_element:
            if child.tag[start_index:] == 'title':
                solr_record['title'] = child.text
            elif child.tag[start_index:] == 'creator':
                solr_record['authors'].append(child.text)
            elif child.tag[start_index:] == 'date':
                solr_record['published_date'].append(child.text)
            elif child.tag[start_index:] == 'identifier' and \
              child.text.startswith('http://arxiv'):
                solr_record['url'] = child.text
                id_startindex = child.text.rfind('/') + 1
                solr_record['arxiv_identifier'] = child.text[id_startindex:]    # Return only the first date (1st element in list): the date of version 1.
        # Append each record in dict form (not defaultdict) to the 
        # list_for_solr list.
        list_for_solr.append(dict(solr_record))
    print(len(list_for_solr))
    solr = pysolr.Solr('http://localhost:8983/solr/arxiv_metadata')
    solr.add(list_for_solr)

if __name__ == '__main__':
    xml_root = get_xml_root()
    parse_xml_insert_into_solr(xml_root)
    