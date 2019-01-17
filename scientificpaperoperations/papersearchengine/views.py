import datetime
import re
from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from .forms import SearchPapersForm, SearchCitedAuthorsForm, SearchCitedPaperForm, SearchAuthorsForm, SearchMetatitleForm
from .django_paper_search_v2 import *
#from .django_paper_search import *

# Create your views here.

def index(request):
    return render(
     request,
    'papersearchengine/index.html',
    )

def phrase_search(request):
    """ Implements  the phrase search by displaying a search form, checking for errors
    and rendering the results in the front-end."""
    # Check if the query field has already been populated. If so, send a get request to
    # the form itself.
    if request.method == 'GET' and request.GET.get('query'):
        form = SearchPapersForm(request.GET)
        # Check if data has been entered already in either query or num_rows
        if form.is_valid():
            # Error handling done by Django. If it's not valid, it just jumps
            # to the render at the end.
            # cleaned is a dict, can be passed in render's context directly if needed
            cleaned = form.cleaned_data
            query = cleaned.get('query')
            numrows = cleaned.get('numrows')
            if numrows is None:
                numrows = 100
            # Render the search results form
            reslist = search_sentences_plus(query, numrows)
            if reslist == []:
                # No results found
                printdict = {'query': query, 'numresults': 0, 'results':[], 'numrows': numrows}
            else:
                results, num_results, num_rows, query  = reslist
                printdict = {'query': query, 'numresults': num_results, 'results':results, 'numrows': numrows}

            return render(request, 'papersearchengine/phrasesearchresults.html', 
                          printdict)
    else:
        form=SearchPapersForm()
    # Render empty form
    return render(request, 'papersearchengine/phrasesearch.html',{'form':form})

def metadatatitle_search(request):
     """ Implements  the metadata title search by displaying a search form, checking for errors
     and rendering the results in the front-end."""
     # Check if the query field has already been populated. If so, send a get request to
     # the form itself.
     if request.method == 'GET' and request.GET.get('query'):
         form = SearchMetatitleForm(request.GET)
         # Check if data has been entered already in either query or num_rows
         if form.is_valid():
             # Error handling done by Django. If it's not valid, it just jumps
             # to the render at the end.
             # cleaned is a dict, can be passed in render's context directly if needed
             cleaned = form.cleaned_data
             query = cleaned.get('query')
             numrows = cleaned.get('numrows')
             if numrows is None:
                 numrows = 100
             reslist = search_meta_titles(query, numrows)
             if reslist == []:
                 # No results found
                 printdict = {'query': query, 'numresults': 0, 'results':[], 'numrows': numrows}
             else:
                 results, num_results, num_rows, query  = reslist
                 printdict = {'query': query, 'numresults': num_results, 'results':results, 'numrows': numrows}

             return render(request, 'papersearchengine/titlesearchresults.html', 
                           printdict)
     else:
         form=SearchMetatitleForm()
     # Render empty form       
     return render(request, 'papersearchengine/titlesearch.html', {'form':form})

def author_search(request):
     """ Implements  the author search by displaying a search form, checking for errors
     and rendering the results in the front-end."""
     # Check if the query field has already been populated. If so, send a get request to
     # the form itself.
     if request.method == 'GET' and request.GET.get('query'):
         form = SearchAuthorsForm(request.GET)
         # Check if data has been entered already in either query or num_rows
         if form.is_valid():
             # Error handling done by Django. If it's not valid, it just jumps
             # to the render at the end.
             # cleaned is a dict, can be passed in render's context directly if needed
             cleaned = form.cleaned_data
             query = cleaned.get('query')
             numrows = cleaned.get('numrows')
             if numrows is None:
                 numrows = 100
             # Split the query to individual authors and remove spaces and send the authors list to 
             # search_authors. 
             authors = query.split(';')
             authors = [author.strip() for author in authors]
             # Create a display string for the query with ANDs between authors.
             displayauthors = ' AND '.join(authors)
             reslist = search_authors(authors, numrows)
             if reslist == []:
                 # No results found
                 printdict = {'query': displayauthors, 'numresults': 0, 'results':[], 'numrows': numrows}
             else:
                 results, num_results, num_rows, query  = reslist
                 printdict = {'query': displayauthors, 'numresults': num_results, 'results':results, 'numrows': numrows}

             return render(request, 'papersearchengine/authorsearchresults.html', 
                           printdict)
     else:
         form=SearchAuthorsForm()
     # Render empty form       
     return render(request, 'papersearchengine/authorsearch.html', {'form':form})

def normalize_results(results):
    """ This func normalizes the published date and authors of metadata so that they are displayed in the right format.
    """
    for result in results:
        # authors is result[1] and published_date is result[4]
        result[1] = '; '.join(result[1])
        # Strip off timestamp (which solr returns with T00... after 10th character, and display in format January 13, 2018 instead
        # of 2018-01-13). Finally, convert the list of dates into a string separated by semicolon and space
        if result[4] is not None and result[4] != []:
            if len(result[4]) == 1:
                result[4] = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in result[4]])
            else:
                result[4] = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in result[4]]) + \
                            ' (multiple dates indicate revisions to the paper)'
        else:
            result[4] = 'No published date found for this result'
    return results

def normalize_date_phrase_search(results):
    """ Normalizes the published date in the results for phrase search. """
    for result in results:
        published_date = result[5]
        if published_date is not None and published_date != []:
            # Strip off timestamp (which solr returns with T00... after 10th character, and display in format March 25, 2018 instead
            # of 2018-03-25). Finally, convert the list of dates into a string separated by semicolon and space
            if len(published_date) == 1:
                print(published_date)
                published_date = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in published_date])
            else:
                print(published_date)
                published_date = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in published_date]) + \
                                    ' (multiple dates indicate revisions to the paper)'
        else:
            published_date = 'No published date found for this result'
        result[5] = published_date
    return results

def cited_author_serach(request):
     """ Implements  the cited author search by displaying a search form, checking for errors
     and rendering the results in the front-end."""
     # Check if the query field has already been populated. If so, send a get request to
     # the form itself.
     if request.method == 'GET' and request.GET.get('query'):
         form = SearchCitedAuthorsForm(request.GET)
         # Check if data has been entered already in either query or num_rows
         if form.is_valid():
             # Error handling done by Django. If it's not valid, it just jumps
             # to the render at the end.
             # cleaned is a dict, can be passed in render's context directly if needed
             cleaned = form.cleaned_data
             query = cleaned.get('query')
             numrows = cleaned.get('numrows')
             if numrows is None:
                 numrows = 100
             # Render the search results form
             reslist = search_references_plus(query, numrows, 'authors')
             if reslist == []:
                 # No results found
                 printdict = {'query': query, 'numresults': 0, 'results':[], 'numrows': numrows}
             else:
                 results, num_results, num_rows, query = reslist
                 # Display only the query (remove the proximity symbol etc.)
                 query = query[:query.rfind('"')+1]
                 printdict = {'query': query, 'results':results, 'numrows': numrows, 'numresults': num_results}
             return render(request, 'papersearchengine/citedauthorsearchresults.html', 
                           printdict)
     else:
         form=SearchCitedAuthorsForm()
     # Render empty form       
     return render(request, 'papersearchengine/citedauthorsearch.html', {'form':form})

def cited_paper_search(request):
     """ Implements  the cited paper search by displaying a search form, checking for errors
     and rendering the results in the front-end."""
     # Check if the query field has already been populated. If so, send a get request to
     # the form itself.
     if request.method == 'GET' and request.GET.get('query'):
         form = SearchCitedPaperForm(request.GET)
         # Check if data has been entered already in either query or num_rows
         if form.is_valid():
             # Error handling done by Django. If it's not valid, it just jumps
             # to the render at the end.
             # cleaned is a dict, can be passed in render's context directly if needed
             cleaned = form.cleaned_data
             query = cleaned.get('query')
             numrows = cleaned.get('numrows')
             if numrows is None:
                 numrows = 100
             # Render the search results form
             reslist = search_references_plus(query, numrows, 'title')
             if reslist == []:
                 # No results found
                 printdict = {'query': query, 'numresults': 0, 'results':[], 'numrows': numrows}
             else:
                 results, num_results, num_rows, query = reslist
                 # Display only the query (remove the proximity symbol etc.)
                 query = query[:query.rfind('"')+1]
                 printdict = {'query': query, 'results':results, 'numrows': numrows, 'numresults': num_results}
             return render(request, 'papersearchengine/citedpapersearchresults.html', printdict)
     else:
         form=SearchCitedPaperForm()
     # Render empty form       
     return render(request, 'papersearchengine/citedpapersearch.html', {'form':form})

def change_dateformat_addoffsets_citation(results):
    """ Changes the date format for all the results from yyyy-mm-dd into Month dd, yyyy; """
    for result in results:
        published_date = result[7].split(';')
        if len(published_date) == 1:
            published_date = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in published_date])
        else:
            published_date = '; '.join([datetime.datetime.strptime(date[:10], '%Y-%m-%d').strftime('%B %d, %Y') for  date in published_date]) +\
                                       ' (multiple dates indicate revisions to the paper)'
        result[7] = published_date
        # Foll. list will be of the form [[sentence1, annotation_index, before_annotation_index, after_annotation_index], [sentence2,...],...]]
        sentence_with_annotations = []
        for sentence in result[2]:
            # sublist will contain 1 sentence, and three sets of indices 
            sublist = []
            match = re.search(result[0], sentence)
            sublist.append(sentence)
            # Find indices of annotation in sentence (separated by :), indices of the sentence before the annotation and
            # indices of the sentence after the annotation, both also separated by a colon.
            # This is used in the template, where {{sentence|slice:annotation_indices}} is used to get the part to highlight the annotation. 
            sublist.extend(["{}:{}".format(match.start(), match.end()), "{}:{}".format(0, match.start()), "{}:".format(match.end())])
            sentence_with_annotations.append(sublist)
        result[2] = sentence_with_annotations
    return results

def about(request):
    """ Displays an About Us page. """
    return render(
     request,
    'papersearchengine/about.html',
    )
