from django import forms

class SearchPapersForm(forms.Form):
    query = forms.CharField(widget = forms.TextInput( 
    attrs={
        'class': 'form-control',
        'placeholder': 'Enter a phrase, e.g., "semantic cognition", "knowledge base completion", "stochastic pooling")',
    }
        ), max_length=100)
    numrows = forms.IntegerField(required=False, min_value=1, max_value=1000, widget = forms.NumberInput(
    attrs={
         'class': 'form-control',
         'placeholder': 'No. of results (default: 100)',
    }))

class SearchCitedAuthorsForm(forms.Form):
    query = forms.CharField(widget = forms.TextInput( 
    attrs={
        'class': 'form-control',
        'placeholder': 'Enter list of cited authors (separated by semicolons) '
    }
        ), max_length=100)
    numrows = forms.IntegerField(required=False, min_value=1, max_value=1000, widget = forms.NumberInput(
    attrs={
         'class': 'form-control',
         'placeholder': 'No. of results (default: 100)'
    }))

class SearchCitedPaperForm(forms.Form):
    query = forms.CharField(widget = forms.TextInput( 
    attrs={
        'class': 'form-control',
        'placeholder': 'Enter title of cited paper (partial titles allowed)'
    }
        ), max_length=100)
    numrows = forms.IntegerField(required=False, min_value=1, max_value=1000, widget = forms.NumberInput(
    attrs={
         'class': 'form-control',
         'placeholder': 'No. of results (default: 100)'
    }))

class SearchMetatitleForm(forms.Form):
    query = forms.CharField(widget = forms.TextInput( 
    attrs={
        'class': 'form-control',
        'placeholder': "Enter paper's title (or part of it), e.g., 'linked data quality'"
    }
        ), max_length=100)
    numrows = forms.IntegerField(required=False, min_value=1, max_value=1000, widget = forms.NumberInput(
    attrs={
         'class': 'form-control',
         'placeholder': 'No. of results (default: 100)'
    }))

class SearchAuthorsForm(forms.Form):
    query = forms.CharField(widget = forms.TextInput( 
    attrs={
        'class': 'form-control',
        'placeholder': "Enter list of authors (separated by semicolons; e.g., 'Tim Berners-Lee')"
    }
        ), max_length=100)
    numrows = forms.IntegerField(required=False, min_value=1, max_value=1000, widget = forms.NumberInput(
    attrs={
         'class': 'form-control',
         'placeholder': 'No. of results (default: 100)'
    }))

