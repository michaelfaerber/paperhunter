from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('phrasesearch/', views.phrase_search, name='phrasesearch'),
    path('phrasesearchresults/', views.phrase_search, name='phrasesearchresults'),
    path('titlesearch/', views.metadatatitle_search, name='metadatatitlesearch'),
    path('titlesearchresults/', views.metadatatitle_search, name='metadatatitlesearchresults'),
    path('authorsearch/', views.author_search, name='authorsearch'),
    path('authorsearchresults/', views.author_search, name='authorsearchresults'),
    path('citedpapersearch/', views.cited_paper_search, name='citedpapersearch'),
    path('citedpapersearchresults/', views.cited_paper_search, name='citedpapersearchresults'),
    path('citedauthorsearch/', views.cited_author_serach, name='citedauthorsearch'),
    path('citedauthorsearchresults/', views.cited_author_serach, name='citedauthorsearchresults'),
    path('about/', views.about, name='about'),
]
