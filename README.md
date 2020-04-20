# PaperHunter: A System for Exploring Papers and Citation Contexts

## Overview
This repository provides the code for a search engine which gives the user the option to do a variety of searches on a set of research papers. Technically, it is based on [Django](https://www.djangoproject.com/), [Apache Solr](https://lucene.apache.org/solr/) and Python.

The following 5 search types are supported by the system:
1. __Search for papers given a phrase.__ Given a phrase (here within the field of computer science), this search functionality allows users to search for all papers on arXiv that contain this phrase in the body text. Thus, this functionality is particularly suitable when papers with very specific keywords (e.g., "semantic cognition," "knowledge base completion," and "stochastic pooling") and not only abstract research topics need to be retrieved. 
2. __Search for papers given a paper's (incomplete) title.__ Given the title of a paper, this search functionality allows users to search for its full metadata. Also, only parts of the paper's title can be provided as inputs. For instance, searching for "linked data quality" allows users to search for all papers on that topic. 
3. __Search for papers given an author's name.__ Given an author's name, this functionality allows users to retrieve the full metadata of all papers written by this author.
4. __Search for citation contexts given the cited paper's title.__ Given any paper's title, this search functionality allows users to retrieve all sentences from the bodies of arXiv papers in which the specified paper is cited. If a publication is cited several times within a paper, then all citation contexts of this paper are grouped together.To allow a quick assessment of the retrieved citation contexts by the user, an icon is presented next to each citation context. This icon indicates the citation context's polarity and can be positive (i.e., the cited paper is praised), neutral, or negative. The citation polarity values were determined offline by using Athar et al.'s approach and data set for training. 
5. __Search for citation contexts given the cited paper's author.__ Here, users can search for the citation contexts (plus the papers' metadata and the links to arXiv.org) in which papers written by the given author were cited. For instance, by searching for "Tim Berners-Lee," our search engine retrieves all contexts in which papers written by Tim Berners-Lee have been cited. We also provide the citation polarity indication for this search functionality. 

For more information, please have a look on our paper [PaperHunter: A System for Exploring Papers and Citation Contexts](README.md#how-to-cite), published at [ECIR 2019](http://ecir2019.org/) (see below).

## Demo 
A demo of the system is available online at http://paperhunter.net/.

## Contact
The system has been designed and implemented by Michael Färber and Ashwath Sampath. Feel free to reach out to us:

[Michael Färber](https://sites.google.com/view/michaelfaerber), michael.faerber@cs&#46;kit&#46;edu

## How to Cite
Please cite our work as follows (see also the [DBLP entry](https://dblp.org/rec/bibtex/conf/ecir/FarberSJ19)):
```
@inproceedings{Faerber2019ECIR,
  author    = {Michael F{\"{a}}rber and
               Ashwath Sampath and
               Adam Jatowt},
  title     = "{PaperHunter: A System for Exploring Papers and Citation Contexts}",
  booktitle = "{Proceedings of the 41th European Conference on Information Retrieval}",
  location  = "{Cologne, Germany}",
  pages     = {246--250},
  year      = {2019}
}
```
