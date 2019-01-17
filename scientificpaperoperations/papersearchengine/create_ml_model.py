from sklearn.externals import joblib
import pandas as pd
import numpy as np
from nltk.corpus import stopwords

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfTransformer, TfidfVectorizer, CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.metrics import f1_score, precision_recall_curve, precision_score
from sklearn.metrics import recall_score, accuracy_score, classification_report, confusion_matrix
from sklearn.externals import joblib


def read_corpus_create_X_and_y():
    """ Reads the corpus supplied by Athar, produce and return a dataframe called X which has sentences from the corpus, and a Series y
    which has the sentiments (labels)."""
    filename = 'citation_sentiment_corpus.txt'
    df = pd.read_csv(filename, sep="\t", skiprows=18, names=['col1', 'col2', 'sentiment', 'sentence'], usecols=['sentiment', 'sentence'])
    #print(df.head())

    # Keep the labels and the sentences separate: y is a Series, X is a data frame
    X = df.drop('sentiment', axis=1)
    y = df.sentiment
    #print(y.head())
    #print(X.head())
    # The division of labels is heavily skewed: o (neutral): 7627, p (positive): 829, n (negative): 280
    #print(y.value_counts())
    return X, y

def create_train_test(X, y):
    """ Splits X and y (dataframe with sentences and Series with labels respectively) into training and test sets."""
    # There's no need of random_state any more when stratify (on the labels) is used, but it's included here anyway
    X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=True, stratify=y, random_state=13, test_size=0.2)
    #print("SHAPES of X_train={}, y_train={}, X_test={}, y_test={}".format(X_train.shape, y_train.shape, X_test.shape, y_test.shape))
    #print("VALUE COUNTS TRAIN AND TEST:")
    #print(y_train.value_counts())
    #print(y_test.value_counts())
    return X_train, X_test, y_train, y_test


def apply_pipeline():
    """ Applies a pipeline of extracting features, applying transformations and running an SGD model. Parameters 
    and hyperparameters have been selected in a different program. """
    text_pipeline = Pipeline([#('vect', CountVectorizer(max_features= None, max_df=0.75, ngram_range=(1, 3), stop_words=None)),
                              ('vect', CountVectorizer(max_features= 50000, max_df=0.75, ngram_range=(1, 3), stop_words=stopwords.words('english'))),
                              ('tfidf', TfidfTransformer()),
                              #('clf', SGDClassifier(alpha=1e-05, loss = 'hinge', max_iter=160))
                              ('clf', SGDClassifier(alpha=0.0001, loss = 'hinge', max_iter=1000))
                              #('clf', SGDClassifier(alpha=1e-06, loss = 'hinge', max_iter=1000))
                              #('clf', LinearSVC(C=0.3, loss='squared_hinge', fit_intercept=False))
                              ])
    return text_pipeline

def train_and_test(X_train, y_train, X_test):
    """ Func which applies training and test pipelines and returns a pd Series of predicted labels"""
    text_pipeline = apply_pipeline()
    # Train/Fit
    text_pipeline.fit(X_train.sentence, y_train)
    # Predict
    y_pred = pd.Series(text_pipeline.predict(X_test.sentence))
    return y_pred, text_pipeline

def calculate_holdoutset_metrics(y_train, y_test, y_pred, text_pipeline):
    """ Calculates a number of metrics on the holdout set after training and getting the predictions."""
    print("Predicted value counts per class (training set): ", y_train.value_counts())
    print(text_pipeline.steps)
    print("Predicted value counts per class (predictions): ", y_pred.value_counts())
    print("Predicted value counts per class (test set): ", y_test.value_counts())
    f1 = f1_score(y_test, y_pred, average=None)
    precision = precision_score(y_test, y_pred, average=None)
    recall = recall_score(y_test, y_pred, average=None)
    accuracy = accuracy_score(y_test, y_pred)
    print("F1={}, Precision={}, Recall={}, Accuracy={}".format(f1, precision, recall, accuracy))
    print(classification_report(y_test, y_pred, target_names=['negative', 'neutral', 'positive'] ))
    print("Confusion matrix: ", confusion_matrix(y_test, y_pred))

def main():
    """ Main function to train and test the model, and finally pickle it"""
    X, y = read_corpus_create_X_and_y()
    X_train, X_test, y_train, y_test = create_train_test(X, y)
    #print(X_train.shape, X_test.shape, y_train.shape, y_test.shape)
    y_pred, text_pipeline = train_and_test(X_train, y_train, X_test)
    calculate_holdoutset_metrics(y_train, y_test, y_pred, text_pipeline)
    # Pickle the model using joblib
    joblib.dump(text_pipeline, 'citation_model_pipeline.joblib')

if __name__ == '__main__':
    main()