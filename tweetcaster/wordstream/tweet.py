import sys
import json
import string
import re
import time
import os
import sys

import tweepy
import pymongo
from nltk.corpus import stopwords
from nltk import regexp_tokenize
from urllib3 import exceptions
from matplotlib import pyplot as plt

from filter_words import get_monograms_freqdist, get_bigrams_freqdist, get_trigrams_freqdist, get_dataframe_dict

from pusher import Pusher

consumer_key = ""
consumer_secret = ""
access_token = ""
access_token_secret = ""

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

client = pymongo.MongoClient('')

db = client.get_default_database()
tweet_collection = db.test_collection

emoticons_str = r"""
	(?:
		[:=;] # Eyes
		[oO\-]? # Nose (optional)
		[D\)\]\(\]/\\OpP] # Mouth
	)"""

regex_str = [
    emoticons_str,
    r'<[^>]+>',  # HTML tags
    r'(?:@[\w_]+)',  # @-mentions
    r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)",  # hash-tags
    r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+',  # URLs

    r'(?:(?:\d+,?)+(?:\.?\d+)?)',  # numbers
    r"(?:[a-z][a-z'\-_]+[a-z])",  # words with - and '
    r'(?:[\w_]+)',  # other words
    r'(?:\S)'  # anything else
]

tokens_regex = re.compile(r'(' + '|'.join(regex_str) + ')', re.VERBOSE | re.IGNORECASE)
punctuation = list(string.punctuation)
stop = stopwords.words('english') + punctuation + ['rt', 'via']

max_tweets = 100000

class CustomStreamListener(tweepy.StreamListener):
    def __init__(self, api, regex, stop_words, collection):
        super(CustomStreamListener, self).__init__()
        self.api = api
        super(tweepy.StreamListener, self).__init__()
        self.db = pymongo.MongoClient().tweets
        self.collection = collection
        self.regex = regex
        self.stop_words = stop_words
        self.top_monograms = {}
        self.top_bigrams = {}
        self.top_trigrams = {}
        self.tokens = []
        self.num_words = 0
        self.df = None

    # plt.show()

    def get_tokens(self):
        return self.tokens

    def get_monograms(self):
        return self.top_monograms

    def get_bigrams(self):
        return self.top_bigrams

    def get_trigrams(self):
        return self.top_trigrams

    def on_data(self, data):
        pusher = Pusher(
            app_id=u'',
            key=u'',
            secret=u''
        )

        temp_tokens = []

        if self.collection.count() == max_tweets:
            self.disconnect()

        data_dict = json.loads(data)
        self.collection.insert(json.loads(data))
        if 'retweeted_status' not in data_dict:
            text = data_dict['text']
            tweets = self.collection.count()

            encoded_text = text.encode('ascii', 'ignore').lower()
            temp_tokens.extend(regexp_tokenize(encoded_text, self.regex, gaps=False))
            filtered_tokens = [term for term in temp_tokens if not term in self.stop_words]

            num_tokens = len(filtered_tokens)
            print 'Tweet num: ' + str(self.collection.count()) + '\n' + encoded_text
            print 'Parsed and filtered: ' + str(filtered_tokens) + ' words'

            self.num_words += num_tokens

            print 'Total tokens: ' + str(self.num_words)

            self.tokens.extend(filtered_tokens)
            self.top_monograms = get_monograms_freqdist(self.tokens)
            self.top_bigrams = get_bigrams_freqdist(self.tokens)
            self.top_trigrams = get_trigrams_freqdist(self.tokens)

            colldata = get_dataframe_dict(self.top_monograms, 5, {}, tweets, self.collection)

            dataframe = colldata[0]
            labels = list(colldata[0].columns.values)
            # print str(time)
            print os.getcwd()

            # with open(os.getcwd() + '\wordstream\static\js\keywords.json', 'w') as outfile:
            #     json.dump(labels, outfile)

            pusher.trigger('my-channel', 'my-event', {
                'message': labels
            })

    def on_error(self, status_code):
        print >> sys.stderr, "Encountered error with status code: ", status_code
        return True

    def on_timeout(self):
        print >> sys.stderr, "Timeout..."
        return True


def main():
    while True:
        try:
            args = sys.argv[1:]
            if not args:
                print "No keywords!"
            else:
                tweet_stream = tweepy.streaming.Stream(auth,
                                                       CustomStreamListener(api, tokens_regex, stop, tweet_collection))
                tweet_stream.filter(languages=["en"], track=["jefferson davis"])
        except exceptions.ProtocolError:
            continue
        except KeyboardInterrupt:
            tweet_stream.disconnect()
            break


if __name__ == '__main__':
    main()
