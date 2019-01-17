    #-------------------------------------------------------------------------------
    # Name:        PaperSearch v2
    # Purpose:     A Django/Solr search engine which can be used to carry out a number of
    #              searches. All functions completely revamped and simplified from v1.
    #              This is becuase different Solr indices are now used. Most of the
    #              complexity has been shifted from querying (this program) to indexing.
    #
    # Author:      Ashwath Sampath
    #
    # Created:     v1: 14-05-2018 : modified continuously afterwards
    #              v2: 20-12-2018: Compoletely new indices built which massively simplify
    #                              this program by doing a lot of the work at index-time.
    # Copyright:   (c) Ashwath Sampath 2018
    #-------------------------------------------------------------------------------

import requests
import copy
import sys
import re
from collections import OrderedDict
import datetime
import pandas as pd
from sklearn.externals import joblib
import emoji

def search_sentences_plus(query, num_rows):
    """ Takes user's query as input, finds all sentences with the given
    phrase, then finds the title, authors and url of the paper from the
    metadata_plus index which is made up of . It also gets the results and
    normalizes it so that correct errors messages are displayed, and fields
    are displayed in the right format. """
    # each result: sentence, filename (arxiv-identifier) and title
    results_df, query, num_results = search_solr(query, num_rows * 10,
                                             'papers_plus', 'sentence', 'exact', 
                                             'published_date desc', None)
    if len(results_df) == 0:
        return []
    # Change the date format of the published_date column to match what we want in the output.
    results_df = change_date_format(results_df, 'published_date')
    results = results_df.values.tolist()
    results = results[:num_rows]
    return results, num_results, num_rows, query
                          
def search_references_plus(query, num_rows, search_type):
    """ Takes user's query as input, finds all references with the given
    author name/title, gets the local citation url and finds sentences in
    which the citations occurred. """
    # If search_type = title, we do an exact search. If search_type = authors, we do 
    # a proximity search with proximity = len(query) + 3 (as there are ands in the author
    # names, and search may be by last name of one author, full name of other author and so on.
    
    # NOTE: results is now a dataframe in v2.
    if search_type == 'title':
        # Return all rows to count no. of citations.
        results_df, query, num_results = search_solr(query, num_rows*10,
                                             'references_plus', 'cited_paper_details',
                                             'proximity_title', 'citing_published_date desc', None)
    
    if search_type == 'authors':
        # Return all rows to count no. of citations.
        results_df, query, num_results = search_solr(query, num_rows*10,
                                                 'references_plus', 'cited_paper_details',
                                                 'proximity_authors', 'citing_published_date desc', None)
    if len(results_df) == 0:
        return []
    # results_df is a df
    # Get sentiment and add it to the end of the citing_sentence column: no separate column
    results_df = get_sentiment_from_model(results_df)
    # Group sentences from the same citing paper together
    grouped_results_df = group_sentences_together(results_df)
    # This is  not the real numresults, it is just sent to the template to prove that numrows 
    # is greater/less than/equal to numresults
    num_results = len(grouped_results_df)
    # Get num_rows rows out of grouped_results_df
    grouped_results_df = grouped_results_df.head(num_rows)
    # Change the date format of the citing_published_date column to match what we want in the output.
    grouped_results_df = change_date_format(grouped_results_df, 'citing_published_date')
    # Add offsets of the location of the annotation in the sentence: append to the list citing_sentence to create a list of lists
    # with offsets included for each sentence (offsets for annotation's location in the sentence)
    # Input [sentence1, sentece2,]
    grouped_results_df['citing_sentence'] = grouped_results_df[['annotation', 'citing_sentence']].apply(addoffsets_citation, axis=1)
    results_list = grouped_results_df.values.tolist()
    return (results_list, num_results, num_rows, query)

def change_date_format(df, column_name):
    """ Converts a column column_name to the format %B %d, %Y from the current format %Y-%m-%d+Timestamp (Solr format) """
    df[column_name] = pd.to_datetime(df[column_name])
    df[column_name] = df[column_name].dt.strftime('%B %d, %Y')
    #print(df[column_name])
    return df

def addoffsets_citation(row):
    """ Adds offsets for the start and end of the annotation in the each sentence of sentence_list. 
    row is a row of the dataframe with columns 'citing_sentence' and 'annotation' """
    # Foll. list will be of the form [[sentence1, annotation_index, before_annotation_index, after_annotation_index], [sentence2,...],...]]
    sentence_list = row.iloc[1]#row.citings_sentence
    annotation = row.iloc[0]#row.annotation
    sentence_with_annotations = []
    for sentence in sentence_list:
        # sublist will contain 1 sentence, and three sets of indices 
        sublist = []
        match = re.search(annotation, sentence)
        sublist.append(sentence)
        # Find indices of annotation in sentence (separated by :), indices of the sentence before the annotation and
        # indices of the sentence after the annotation, both also separated by a colon.
        # This is used in the template, where {{sentence|slice:annotation_indices}} is used to get the part to highlight the annotation. 
        sublist.extend(["{}:{}".format(match.start(), match.end()), "{}:{}".format(0, match.start()), "{}:".format(match.end())])
        sentence_with_annotations.append(sublist)
    return sentence_with_annotations

def get_sentiment_from_model(df):
    """ Takes a list of lists of results, converts it into a df, and gets the citation polarity from a machine learning
    (SGDClassifier) model learned previously. This is appended at the end of the sentence and the results are converted
    back to the orig form and returned."""
    # Convert the list of lists into a dataframe, replace missing values (Nones are converted into NaNs when a dataframe is created)
    text_pipeline = joblib.load('papersearchengine/citation_model_pipeline.joblib')
    # Read the pipeline from the pickle (joblib)
    #text_pipeline = joblib.load('papersearchengine/citation_model_pipeline_v2.joblib')
    # Preprocess: add polar word (neg + pos) counts
    #positive_polarity_words, negative_polarity_words = read_polar_phrases()
    #df[['processed', 'num_negative_words', 'num_positive_words']] = processing(df.sentence, positive_polarity_words, negative_polarity_words)
    #df['sentiment'] = text_pipeline.predict(df[['sentence', 'processed', 'num_negative_words', 'num_positive_words']])
    df['sentiment'] = text_pipeline.predict(df.citing_sentence)
    # Map sentiment symbol to the actual sentiment
    # Map sentiment symbol to the actual sentiment
    #sentiment_mapping = {'o': emoji.emojize(' (:first_quarter_moon:)', use_aliases=True), 
    #                     'n': emoji.emojize(' (:new_moon:)', use_aliases=True),
    #                     'p': emoji.emojize(' (:full_moon:)', use_aliases=True)}
    sentiment_mapping = {'o': emoji.emojize(' (:hand:)', use_aliases=True), 
                         'n': emoji.emojize(' (:thumbsdown:)', use_aliases=True),
                         'p': emoji.emojize(' (:thumbsup:)', use_aliases=True)}
    df['sentiment'] = df['sentiment'].map(sentiment_mapping)
    # Concatenate the sentiment column to the end of the sentence column, and drop the sentiment column
    df.citing_sentence = df.citing_sentence.str.cat(df.sentiment)
    df = df.drop('sentiment', axis=1)
    return df

def group_sentences_together(df):
    """ Takes a list of lists of results which may include multiple sentences from the same CITING paper, and groups them
    together in a list. The final list of lists which is returned will have fewer or equal results as the input list."""
    
    # Drop duplicate rows based on citing_arxiv identifier, citing_sentence and annotation
    dropbasedoncols = ['citing_arxiv_identifier', 'citing_sentence', 'annotation']
    df = df.drop_duplicates(subset=dropbasedoncols)

    # Convert the list of lists into a dataframe, replace missing values (Nones are converted into NaNs when a dataframe is created)

    groupby_list = ['citing_published_date', 'citing_arxiv_identifier', 'citing_paper_title', 'citing_paper_authors', 
                    'citing_arxiv_url', 'citing_revision_dates', 'citing_dblp_url', 'annotation', 'cited_paper_details']

    df_grouped = pd.DataFrame(df.groupby(groupby_list, sort=False)['citing_sentence'].apply(list)).reset_index()
    # Reorder the columns
    cols = ['annotation', 'cited_paper_details', 'citing_sentence', 'citing_arxiv_identifier', 'citing_paper_title',
            'citing_paper_authors', 'citing_arxiv_url', 'citing_published_date', 'citing_revision_dates', 'citing_dblp_url']
    df_grouped = df_grouped[cols]
    return df_grouped

def flatten_dates_modify_annotations(results):
    """ Flattens the published_date list for all the results into as string in which multiple dates are separated by semicolons.
    The date format is not changed, but the timestamp is removed. Angular brackets are added to the annotation as well for all 
    the results. The results list is then returned."""
    for result in results:
        published_date = result[7]
        if published_date is not None and published_date != []:
            # Strip off timestamp (which solr returns with T00... after 10th character, and convert the list of dates into a string
            # separated by semicolon.
            published_date = ';'.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%Y-%m-%d') for  date in published_date])
        else:
            published_date = 'No published date found for this result'
        result[7] = published_date
        # Solr has removed the angular brackets in the annotation, put them back.
        result[0] = "<{}>".format(result[0])
    return results

def search_authors(query, num_rows):
    """ Returns all metadata (title, authors, urls) when names of 1 or more
    authors are given in the user query. """
    results_df, query, num_results = search_solr(query, num_rows * 10,
                                             'metadata_plus', 'authors', 'and', 
                                             'published_date desc', None)
    if len(results_df) == 0:
        return []
    # Change the date format of the published_date column to match what we want in the output.
    results_df = change_date_format(results_df, 'published_date')
    results = results_df.values.tolist()
    results = results[:num_rows]
    return results, num_results, num_rows, query

def search_meta_titles(query, num_rows):
    """ Returns all metadata (title, authors, url) when a partial or
    complete title is given in the user query. """
    
    results_df, query, num_results = search_solr(query, num_rows * 10,
                                             'metadata_plus', 'title', 'exact', 
                                             'published_date desc', None)
    if len(results_df) == 0:
        return []
    
    # Change the date format of the published_date column to match what we want in the output.
    results_df = change_date_format(results_df, 'published_date')
    results = results_df.values.tolist()
    results = results[:num_rows]
    return results, num_results, num_rows, query

def add_query_type(query, query_type):
    """ Returns the query based on the query type (exact or proximity)
    required for different searches. """
    if query_type == 'exact':
        query = '"' + query + '"'
    elif query_type == 'proximity_authors':
        # Allow for the words in the query to be in a different order. There may also be an
        # 'and' between the words in the file/index. This also allows for search by last name
        # of 1 author and full name of third author.
        query = '"' + query + '"' + '~' + str(len(query.split())+8)
    elif query_type == 'proximity_title':
        # Allow for the words in the query to be in a different order. There may also be an
        # 'and' between the words in the file/index. This also allows for search by last name
        # of 1 author and full name of third author.
        query = '"' + query + '"' + '~' + str(len(query.split()))
    
    elif query_type == 'and':
        # query is a list, authors search
        query = ['"' + name + '"~' + str(len(name.split()) + 1) for name in query]
        query = ' AND '.join(query)
    return query

def search_solr(query, num_rows, collection, search_field, query_type, sort_field=None, filter_query=None):
    """ Creates a URL to call Solr along with the search query, search field
    and number of rows as parameters, and sends a GET request to SOLR. It
    then calls the parse_json func to parse the json, and returns results
    from that function."""
    solr_url = 'http://localhost:8983/solr/' + collection + '/select'
    query = add_query_type(query, query_type)
    if sort_field is not None:
        url_params = {'q': query, 'rows': num_rows, 'df': search_field, 'sort': sort_field}
    else:
        url_params = {'q': query, 'rows': num_rows, 'df': search_field}
    solr_response = requests.get(solr_url, params=url_params)
    if solr_response.ok:
        data = solr_response.json()
        return parse_json(data, collection)
    else:
        print("Invalid response returned from Solr")
        sys.exit(11)

def parse_json(data, collection):
    """ Calls the appropriate json parser based on the collection,
    returns whatever the parser returns, along with the query and
    num_responses, which it gets from the json response. If there
    are no results, it returns ([], query, 0)"""
    # query is the actual phrase searched in Solr
    query = data['responseHeader']['params']['q']
    num_responses = data['response']['numFound']
    if num_responses == 0:
        if collection in ('references_plus', 'metadata_plus', 'papers_plus'):
            return(pd.DataFrame(), query, 0)
        else:
            return ([], query, 0)
    if collection == 'papers':
        results = parse_sentence_json(data)
    elif collection == 'arxiv_metadata':
        results = parse_arxiv_metadata_json(data)
    elif collection == 'metadata':
        results = parse_metadata_json(data)
    elif collection == 'references':
        results = parse_refs_json(data)
    elif collection == 'references_plus':
        results = parse_references_plus_json(data)
    elif collection == 'papers_plus':
        results = parse_papers_plus_json(data)
    elif collection == 'metadata_plus':
        results = parse_metadata_plus_json(data)            
    return (results, query, num_responses)

def parse_sentence_json(data):
    """ Function to parse the json response from the papers collection
    in Solr. It returns the results as a list with the sentence, file name
    and title."""
    # docs contains sentence, fileName, id generated by Solr
    docs = data['response']['docs']
    # Create a list object for the results with sentence, fileName and title
    res 
    ults = [[docs[i].get('sentence')[0], docs[i].get('fileName')]
                for i in range(len(data['response']['docs']))]
    return results

def parse_arxiv_metadata_json(data):
    """ Function to parse the json response from the metadata or the
    arxiv_metadata collections in Solr. It returns the results as a
    list with the sentence, file name and title."""
    # docs contains authors, title, id generated by Solr, url
    docs = data['response']['docs']
    # NOTE: there are records without authors and urls. This is why the
    # get method is always used to get the value instead of getting the value
    # by applying the [] operator on the key.
    results = [[docs[i].get('title'), docs[i].get('authors'),
                docs[i].get('url'), docs[i].get('arxiv_identifier'), 
                docs[i].get('published_date')]
                for i in range(len(data['response']['docs']))]
    return results
    
def parse_metadata_json(data):
    """ Function to parse the json response from the metadata or the
    arxiv_metadata collections in Solr. It returns the results as a
    list with the sentence, file name and title."""
    # docs contains authors, title, id generated by Solr, url
    docs = data['response']['docs']
    # NOTE: there are records without authors and urls. This is why the
    # get method is always used to get the value instead of getting the value
    # by applying the [] operator on the key.
    # Note: '0' is set as a dummy published_date because the preferred metadata
    # (arxiv metadata) returns that field.
    results = [[docs[i].get('title'), docs[i].get('authors'),
                docs[i].get('url'), docs[i].get('arxiv_identifier')]
                for i in range(len(data['response']['docs']))]
    return results

def parse_refs_json(data):
    """ Function to parse the json response from the references collection
    in Solr. It returns the results as a list with the annotation and details.
    """
    # docs contains annotation, fileName, details, id generated by Solr
    docs = data['response']['docs']
    # Create a list object for the results with annotation and details. Details is a list of 
    # a single string, flatten it: remove the string from the list.
    results = [[docs[i].get('annotation'), docs[i].get('details')[0]]
                      for i in range(len(data['response']['docs']))]
    #results = [result[0] for result in results]
    return results


def parse_references_plus_json(data):
    """ Function which parses the references_plus json and returns a pandas dataframe of the
    results.
    Solr Field definition shown below: 
     <!-- REFS file fields: cited paper-->
    <field name="annotation" type="string" indexed="true" stored="true" multiValued="false"/> 
    <field name="cited_paper_details" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <!-- Insert this only for debugging, to search for records from a particular file-->
    <field name="reference_filename" type="string" indexed="false" stored="true" multiValued="false"/> 

    <!-- Citing paper fields: papers, metadata, arxiv_metadata -->
    <!-- Papers -->
    <field name="citing_sentencenum" type="pint" indexed="true" stored="true" multiValued="false"/>
    <field name="citing_sentence" type="text_classic" indexed="true" stored="true" multiValued="false"/>
    <field name="citing_arxiv_identifier" type="string" indexed="true" stored="true" multiValued="false"/>
    
    <!-- arxiv metadata-->
    <field name="citing_arxiv_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    <field name="citing_paper_authors" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="citing_paper_title" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="citing_published_date" type="daterange" indexed="true" stored="true" multiValued="true"/>
    <field name="citing_revision_dates" type="string" indexed="true" stored="true" multiValued="false"/> 

    <!-- meta field: dblp_url-->
    <field name="citing_dblp_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    """
    docs = data['response']['docs']
    docs_df = pd.DataFrame(docs)
    docs_df = docs_df.drop(['_version_', 'id'], axis=1)
    return docs_df

def parse_papers_plus_json(data):
    """ Function which parses the papers_plus json and returns a pandas dataframe of the results.
    Solr Field definition shown below: 
        <!-- Citing paper fields: papers, metadata, arxiv_metadata -->
    <!-- Papers -->
    <field name="sentencenum" type="pint" indexed="true" stored="true" multiValued="false"/>
    <field name="sentence" type="text_classic" indexed="true" stored="true" multiValued="false"/>
    <field name="arxiv_identifier" type="string" indexed="true" stored="true" multiValued="false"/>
    
    <!-- arxiv metadata-->
    <field name="arxiv_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    <field name="authors" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="title" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="published_date" type="pdate" indexed="true" stored="true" multiValued="false"/>
    <field name="revision_dates" type="string" indexed="true" stored="true" multiValued="false"/>

    <!-- meta field: dblp_url-->
    <field name="dblp_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    """
    docs = data['response']['docs']
    docs_df = pd.DataFrame(docs)
    docs_df = docs_df.drop(['_version_', 'id'], axis=1)
    return docs_df

def parse_metadata_plus_json(data):
    """ Function which parses the papers_plus json and returns a pandas dataframe of the results.
    Solr Field definition shown below: 
        <!-- Citing paper fields: papers, metadata, arxiv_metadata -->
    <!-- Papers -->
    <field name="sentencenum" type="pint" indexed="true" stored="true" multiValued="false"/>
    <field name="sentence" type="text_classic" indexed="true" stored="true" multiValued="false"/>
    <field name="arxiv_identifier" type="string" indexed="true" stored="true" multiValued="false"/>
    
    <!-- arxiv metadata-->
    <field name="arxiv_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    <field name="authors" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="title" type="text_classic" indexed="true" stored="true" multiValued="false"/> 
    <field name="published_date" type="pdate" indexed="true" stored="true" multiValued="false"/>
    <field name="revision_dates" type="string" indexed="true" stored="true" multiValued="false"/>

    <!-- meta field: dblp_url-->
    <field name="dblp_url" type="string" indexed="true" stored="true" multiValued="false"/> 
    """
    docs = data['response']['docs']
    docs_df = pd.DataFrame(docs)
    docs_df = docs_df.drop(['_version_'], axis=1)
    return docs_df