# -*- coding: utf-8 -*-
"""
    #-------------------------------------------------------------------------------
    # Name:        INSERT METADATA (JSON FILES) INTO SOLR
    # Purpose:     Module which opens 90238 metadata files: which are in json 
    #              and have the fields 'title', 'authors' (array) and 'url, and
    #              inserts them into Apache Solr.
    #
    # Author:      Ashwath Sampath
    #
    # Created:     20-06-2018
    # Copyright:   (c) Ashwath Sampath 2018
    #-------------------------------------------------------------------------------

"""
import json
import os
import pysolr
from glob import iglob

def insert_metadata_into_solr():
    solr = pysolr.Solr('http://localhost:8983/solr/metadata')    
    basepath = '/home/ashwath'
    folderpath = os.path.join(basepath, 'arxiv-cs-dataset-LREC2018')
    list_for_solr = []
    for filepath in iglob(os.path.join(folderpath, '*.meta')):
        with open(filepath, 'r') as file:
            filename = os.path.basename(filepath)
            filename_without_extension = '.'.join(filename.split('.')[:2])
            content = json.load(file)
            #print(content['title'], content['authors'], content['url'], filename)
        solr_content = {}
        solr_content['authors'] = content['authors']
        solr_content['title'] = content['title']
        solr_content['url'] = content['url']
        solr_content['filename'] = filename_without_extension
        list_for_solr.append(solr_content)
        #solr.add([solr_content])

    solr.add(list_for_solr)
    
if __name__ == '__main__':
    insert_metadata_into_solr()