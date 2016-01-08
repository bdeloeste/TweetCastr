import pymongo
import json
import tweepy
import os

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.core.urlresolvers import reverse

from django.views.static import serve
# Create your views here.

from .forms import SearchForm

client = pymongo.MongoClient('')

db = client.get_default_database()
collection = db.test_collection

consumer_key = ""
consumer_secret = ""
access_token = ""
access_token_secret = ""

pusher_app_id = ""
pusher_key = ""
pusher_secret = ""

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

config_path = "wordstream/static/js/config.js"
submit_path = "wordstream/static/js/submit.json"

def index(request):
    # if request.GET.get('home_button'):
    tweet_text = collection.find({}).limit(50)
    print type(tweet_text)
    form = SearchForm()
    header = 'Real-time Keyword Analysis'
    context = {'tweet_text': tweet_text, 'form': form, 'header': header}
    file_exist = os.path.isfile(config_path)
    if file_exist:
        os.remove(config_path)
    submit_exist = os.path.isfile(submit_path)
    with open(submit_path, "w") as outfile:
        json.dump({'submit': False}, outfile)
    if request.method == 'POST':
        context.update({'plot': True})
    return render(request, 'wordstream/index.html', context)

def plot(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            keywords = form.cleaned_data['keyword']
            keyword_list = keywords.split(' ')
            context = {'keywords': keywords}
            if keywords == 'Enter keyword(s)':
                header = 'You did not enter any keywords.'
                form = SearchForm()
                context.update({'header': header, 'form': form})
                return render(request, 'wordstream/plot.html', context)
            header = 'Here\'s your plot with keyword: ' + str(keywords)
            context.update({'header': header})
            with open(submit_path, "w") as out:
                json.dump({'submit': True}, out)
            with open(config_path, "w") as outfile:
                # TODO: FINISH CONFIG LINE
                outfile.write('module.exports = {pusher_app_id: \"' + pusher_app_id + '\", pusher_key: \"' + pusher_key + '\", pusher_secret: \"' + pusher_secret + '\", twitter_consumer_key: \"' + consumer_key + '\", twitter_consumer_secret: \"' + consumer_secret + '\", twitter_access_token_key: \"' + access_token + '\", twitter_access_token_secret: \"' + access_token_secret + '\", keywords: ')
                json.dump(keyword_list, outfile)
                outfile.write('}')
            return render(request, 'wordstream/plot.html', context)
    return HttpResponse("Displaying tweets with keyword")

def download(request):
    # filepath = 'wordstream/static/js/config.js'
    # return serve(request, os.path.basename(filepath), os.path.dirname(filepath))
    file = open("wordstream/static/js/config.js").read()
    print file
    response = HttpResponse(file, content_type='application/javascript')
    response['Content-Disposition'] = 'attachment; filename="config.js"'
    return response

def tweets(request, keyword):
    return HttpResponse("Displaying tweets with keyword %s." % keyword)
