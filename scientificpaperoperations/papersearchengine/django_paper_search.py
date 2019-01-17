    #-------------------------------------------------------------------------------
    # Name:        Research papers search engine
    # Purpose:     A search engine which can search different fields.
    #
    # Author:      Ashwath Sampath
    #
    # Created:     14-05-2018
    # Copyright:   (c) Ashwath Sampath 2018
    #-------------------------------------------------------------------------------

import requests
import copy
import sys
from collections import OrderedDict
import datetime
import pandas as pd
from sklearn.externals import joblib
import emoji

def search_sentences(query, num_rows):
    """ Takes user's query as input, finds all sentences with the given
    phrase, then finds the title, authors and url of the paper from the
    arxiv_metadata and metadata indices. It also gets the results and
    normalizes it so that correct errors messages are displayed, and fields
    are displayed in the right format. """
    # each result: sentence, filename (arxiv-identifier) and title
    results, query, num_results = search_solr(query, num_rows,
                                             'papers', 'sentence', 'exact')
    if results == []:
        return results
    for result in results:
        # Get the papers index file name (arxiv_identifier).
        arxiv_identifier = result[1]
        # Note: for the following call, only 1 result will be returned, as it's an 
        # exact match search on arxiv_identifier. The num_rows attribute is 
        # irrelevant, and can take any value >= 1.
        res_arxiv, _, _ = search_solr(arxiv_identifier, 1,
                                'arxiv_metadata', 'arxiv_identifier', 'exact')
        res_dblp, _, _ = search_solr(arxiv_identifier, 1,
                                'metadata', 'arxiv_identifier', 'exact')
        if res_arxiv == []:
            # Not found in arxiv_metadata
            if res_dblp == []:
                # Not found in metadata index too
                # title, authors, arxiv url, published date, dblp url
                result.extend(['No title found for this result', 'No author metadata found for this result', 
                    'No Arxiv URL found for this result', 'No published date found for this result', None])
            else:
                # found in metadata index
                dblp_url = res_dblp[0][2] if res_dblp[0][2] != '' and res_dblp[0][2] is not None else None
                title = res_dblp[0][0] if res_dblp[0][0] != '' and res_dblp[0][0] is not None else 'No title found for this result'
                authors = '; '.join(res_dblp[0][1]) if res_dblp[0][1] != [] and res_dblp[0][1] is not None else 'No author metadata found for this result'

                result.extend([title, authors, 'No arXiV URL found for this result', 'No published date found for this result', dblp_url])

        else:
            # res contains title, authors, url, arxiv_identifier, published_date (from arxiv_metadata) 
            # Note: authors and published_date are lists.
            title, authors, arxiv_url, arxiv_identifier, published_date = res_arxiv[0]
            # Normalize the fields except published_date, which is normalized later in Django views (as it should be sorted before normalizing)
            title = title if title != '' and title is not None else 'No title found for this result'
            authors = '; '.join(authors) if authors != [] and authors is not None else 'No author metadata found for this result'
            arxiv_url = arxiv_url if arxiv_url is not None and arxiv_url != '' else 'No arXiV URL found for this result'

            if res_dblp == []:
                result.extend([title, authors, arxiv_url, published_date, None])
            else:
                dblp_url = res_dblp[0][2] if res_dblp[0][2] != '' and res_dblp[0][2] is not None else None
                result.extend([title, authors, arxiv_url, published_date, dblp_url])
    results.sort(key=lambda x: x[5][0], reverse=True)
    return results, query, num_rows, num_results
                          
def search_references(query, num_rows, search_type):
    """ Takes user's query as input, finds all references with the given
    author name/title, gets the local citation url and finds sentences in
    which the citations occurred. """
    # If search_type = title, we do an exact search. If search_type = authors, we do 
    # a proximity search with proximity = len(query) + 3 (as there are ands in the author
    # names, and search may be by last name of one author, full name of other author and so on.
    
    if search_type == 'title':
        # Return all rows to count no. of citations.
        results, query, num_results = search_solr(query, 100000,
                                             'references', 'details',
                                             'proximity_title')
    
    if search_type == 'authors':
        # Return all rows to count no. of citations.
        results, query, num_results = search_solr(query, 100000,
                                                 'references', 'details',
                                                 'proximity_authors')
    num_total_citations = len(results)
    if results == []:
        return []
    # Create a dict of unique citations to be searched in the papers collection. 
    # Use an OrderedDict comprehension (unique key: annotation, value: details. If the same
    # annotation occurs different times with different details, only the fist 'details'
    # is added into the dict.
    unique_citations = OrderedDict((result[0], result[1]) for result in results)
    num_unique_citations = len( unique_citations)
    # Convert unique_citations back into a list -- a list of tuples so that we can slice it.
    unique_citations = list(unique_citations.items())
    # Do not query all annotations in the papers index, keep only a max. of num_rows * 3
    # unique citations. If num_rows * 3 is greater than the no. of unique citations, keep
    # all the unique citations.
    if num_rows * 3 < num_unique_citations:
        unique_citations = unique_citations[:num_rows*3]
    final_results = []
    for annotation, details in unique_citations:
        reslist = search_sentences(annotation, num_rows)
        if reslist == []:
            # If the annotation was not found, go to next annotation
            continue
        res = reslist[0]
        # Append all the intermediate fields into intermediate results. This list will later be 
        # the final_results list.
        # Append all the fields like title, sentence, arxiv url etc. from papers
        # and metadata/arxiv_metadata indexes
        for entry in res:
            # res is a list of lists -> entry is a list: extract values from entry
            intermediate_result = []
            intermediate_result.append(annotation)
            intermediate_result.append(details)
            # Values of 1 result: title, authors etc.
            for value in entry:
                intermediate_result.append(value)
            # Append the current result to final_results. final_result contains full lists.
            final_results.append(intermediate_result)
    
    final_results = flatten_dates_modify_annotations(final_results)
    # Get sentiment
    final_results = get_sentiment_from_model(final_results)
    final_results = group_sentences_together(final_results)
    result_counter = len(final_results)
    final_results = final_results[:num_rows] 
    final_results.sort(key=lambda x: x[7].split(';')[0], reverse=True)     
    return (final_results, result_counter, num_rows, query)

def read_polar_phrases():
    """ Reads a file of positive/negative words, return 2 separate lists of positive and negative words resp."""
    # Open positive and negative polarity list file.
    polarity_df = pd.read_csv('polar_phrases.txt', sep='\t', names=['polar_word', 'polarity'])
    #polarity_df.set_index('polar_word', inplace=True, drop=True)
    negative_polarity_df = polarity_df[polarity_df.polarity==-1]
    positive_polarity_df = polarity_df[polarity_df.polarity==1]
    positive_polarity_words = polarity_df.polar_word.tolist()
    negative_polarity_words = negative_polarity_df.polar_word.tolist()
    return positive_polarity_words, negative_polarity_words

def processing(df, positive_polarity_words, negative_polarity_words):
    """ Does pre-processing on a dataframe"""
    # Remove punctuation using re.sub(pattern, replace, input): \w: letter/num/underscore, \s: space. Also, make everything lowercase
    df['processed'] = df['sentence'].apply(lambda x: re.sub(r'[^\w\s]', '', x.lower()))
    
    # Numerical features: these will need to be scaled in the pipeline
    df['num_negative_words'] = df['processed'].apply(lambda sen: sum([1 if sen.find(word) != -1 else 0 for word in negative_polarity_words]))
    df['num_positive_words'] = df['processed'].apply(lambda sen: sum([1 if sen.find(word) != -1 else 0 for word in positive_polarity_words]))
    return df[['processed', 'num_negative_words', 'num_positive_words']]

def get_sentiment_from_model(results):
    """ Takes a list of lists of results, converts it into a df, and gets the citation polarity from a machine learning
    (SGDClassifier) model learned previously. This is appended at the end of the sentence and the results are converted
    back to the orig form and returned."""
    # Convert the list of lists into a dataframe, replace missing values (Nones are converted into NaNs when a dataframe is created)
    df = pd.DataFrame(results, columns=['annotation', 'details', 'sentence', 'arxiv_identifier', 'title', 'authors', 'arxiv_url', 'published_date', 'dblp_url'])
    text_pipeline = joblib.load('papersearchengine/citation_model_pipeline.joblib')
    # Read the pipeline from the pickle (joblib)
    #text_pipeline = joblib.load('papersearchengine/citation_model_pipeline_v2.joblib')
    # Preprocess: add polar word (neg + pos) counts
    #positive_polarity_words, negative_polarity_words = read_polar_phrases()
    #df[['processed', 'num_negative_words', 'num_positive_words']] = processing(df.sentence, positive_polarity_words, negative_polarity_words)
    #df['sentiment'] = text_pipeline.predict(df[['sentence', 'processed', 'num_negative_words', 'num_positive_words']])
    df['sentiment'] = text_pipeline.predict(df.sentence)
    # Map sentiment symbol to the actual sentiment
    # Map sentiment symbol to the actual sentiment
    sentiment_mapping = {'o': emoji.emojize(' (:hand:)', use_aliases=True), 
                         'n': emoji.emojize(' (:thumbsdown:)', use_aliases=True),
                         'p': emoji.emojize(' (:thumbsup:)', use_aliases=True)}

    df['sentiment'] = df['sentiment'].map(sentiment_mapping)
    # Concatenate the sentiment column to the end of the sentence column, and drop the sentiment column
    df.sentence = df.sentence.str.cat(df.sentiment)
    df = df.drop('sentiment', axis=1)
    results_list = df.values.tolist()
    return results_list

def group_sentences_together(results):
    """ Takes a list of lists of results which may include multiple sentences from the same CITING paper, and groups them
    together in a list. The final list of lists which is returned will have fewer or equal results as the input list."""
    # Convert the list of lists into a dataframe, replace missing values (Nones are converted into NaNs when a dataframe is created)
    df=pd.DataFrame(results, columns=['annotation', 'details', 'sentence', 'arxiv_identifier', 'title', 'authors', 'arxiv_url', 'published_date', 'dblp_url'])
    df['dblp_url'].fillna('dummy value', inplace=True)
    df_grouped = pd.DataFrame(df.groupby(['arxiv_identifier', 'title', 'authors', 'arxiv_url',
                                          'published_date', 'dblp_url', 'annotation', 'details'])['sentence'].apply(list)).reset_index()
    # Reorder the columns
    cols = ['annotation', 'details', 'sentence', 'arxiv_identifier', 'title', 'authors', 'arxiv_url', 'published_date', 'dblp_url']
    df_grouped = df_grouped[cols]
    grouped_list = df_grouped.values.tolist()
    for result in grouped_list:
        result[8] = None if result[8] == 'dummy value' else result[8]
    return grouped_list

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
    """ Returns all metadata (title, authors, url) when names of 1 or more
    authors are given in the user query. """
    results, query, num_results = search_solr(query, num_rows,
                                             'arxiv_metadata', 'authors',
                                             'and')
    for result in results:
            arxivid = result[3]
            # This should return only 1 row (exact match on arxiv_identifier
            res_dblp, _, _ = search_solr(arxivid, 1, 'metadata', 'arxiv_identifier', 'exact')
            # We want the dblp identifier, i.e. the url. It is the 3rd element in res_dblp,
            # i.e. index 2. Add this to results. As res_dblp is a list of lists (it is generally meant 
            # for multiple results), we need res_dblp[0][2]
            dblp_url = None if res_dblp == [] else res_dblp[0][2]
            # Also, the dblp_url may have no value (None or "") in the metadata file/index, check for this.
            dblp_url = dblp_url if dblp_url != '' and dblp_url is not None else None
            result.append(dblp_url)
    # 5th element of the list is published_date, which might contain one or more dates (as strings with
    # timestamp). Sort the whole list according to the first element of this date, i.e. result[4][0]
    results.sort(key=lambda x: x[4][0], reverse=True)
    return results, num_results, num_rows

def search_meta_titles(query, num_rows):
    """ Returns all metadata (title, authors, url) when a partial or
    complete title is given in the user query. """
    results, query, num_results = search_solr(query, num_rows,
                                             'arxiv_metadata', 'title',
                                             'exact')
    for result in results:
            arxivid = result[3]
            # This should return only 1 row (exact match on arxiv_identifier
            res_dblp, _, _ = search_solr(arxivid, 1, 'metadata', 'arxiv_identifier', 'exact')
            # We want the dblp identifier, i.e. the url. It is the 3rd element in res_dblp,
            # i.e. index 2. Add this to results. As res_dblp is a list of lists (it is generally meant 
            # for multiple results), we need res_dblp[0][2]
            if res_dblp == []:
                dblp_url = "No DBLP URL found for this result"
            else:
                dblp_url = res_dblp[0][2]
            result.append(dblp_url)
    results.sort(key=lambda x: x[4][0], reverse=True)
    return results, num_results, num_rows

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
        query = ['"' + name + '"~' + str(len(name.split())) for name in query]
        query = ' AND '.join(query)
    return query

def search_solr(query, num_rows, collection, search_field, query_type):
    """ Creates a URL to call Solr along with the search query, search field
    and number of rows as parameters, and sends a GET request to SOLR. It
    then calls the parse_json func to parse the json, and returns results
    from that function."""
    solr_url = 'http://localhost:8983/solr/' + collection + '/select'
    query = add_query_type(query, query_type)
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
        return ([], query, 0)
    if collection == 'papers':
        results = parse_sentence_json(data)
    elif collection == 'arxiv_metadata':
        results = parse_arxiv_metadata_json(data)
    elif collection == 'metadata':
        results = parse_metadata_json(data)
    elif collection == 'references':
        results = parse_refs_json(data)
    return (results, query, num_responses)

def parse_sentence_json(data):
    """ Function to parse the json response from the papers collection
    in Solr. It returns the results as a list with the sentence, file name
    and title."""
    # docs contains sentence, fileName, id generated by Solr
    docs = data['response']['docs']
    # Create a list object for the results with sentence, fileName and title
    results = [[docs[i].get('sentence')[0], docs[i].get('fileName')]
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
