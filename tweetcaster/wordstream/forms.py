from django import forms

class SearchForm(forms.Form):
    keyword = forms.CharField(label='', initial='Enter keyword(s)', max_length=100)
