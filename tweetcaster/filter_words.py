import json
import string
import re
from collections import OrderedDict

import pandas
import matplotlib.pyplot as plt
from progressbar import AnimatedMarker, Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from nltk.corpus import stopwords
from nltk import FreqDist
from nltk import regexp_tokenize
from nltk import bigrams, trigrams
from pymongo import MongoClient
from dateutil.parser import parse
from pymongo.errors import CursorNotFound
import mpld3
from datetime import datetime

import time
import calendar

def remove_quoted_text(query, num_tweets, collection):
    count = 0

    str_in_quotations_regex = re.compile(r'\"(.+?)\"', re.IGNORECASE)

    cursor = collection.find(query, no_cursor_timeout=True, batch_size=75)

    widgets = ['Removing quoted text ', Percentage(), ' ', Bar(marker=AnimatedMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]

    progress_bar = ProgressBar(widgets=widgets, maxval=num_tweets).start()

    for tweet in cursor.limit(num_tweets):
        try:
            text = tweet['text'].encode('ascii', 'ignore').lower()
            str_in_quotations = str_in_quotations_regex.sub('', text)

            collection.update({'_id': tweet['_id']}, {'$set': {'text': str_in_quotations}})
        except CursorNotFound:
            pass
        progress_bar.update(count + 1)
        count += 1
    progress_bar.finish()
    cursor.close()


def parse_tweets(query, regex, stop_words, num_tweets, collection, get_filtered_keywords, keyword):
    tokens = []
    temp_tokens = []
    filtered_tokens = []
    final_filtered_tokens = []
    keyword = keyword.lower()
    count = 0
    keyword_count = 0
    source_regex = re.compile(r'<.*?>')

    if get_filtered_keywords:
        widget_start = 'Filtering tokens: '
    else:
        widget_start = 'Getting word frequencies with keyword: ' + keyword

    token_cursor = collection.find(query, no_cursor_timeout=True, batch_size=200)

    # Command line progress bar init
    widgets_tokens = [widget_start, Percentage(), ' ', Bar(marker=AnimatedMarker()),
                      ' ', ETA(), ' ', FileTransferSpeed()]

    progress_bar_tokens = ProgressBar(widgets=widgets_tokens, maxval=num_tweets).start()

    for tweet in token_cursor.limit(num_tweets):
        try:
            # Convert text attribute of tweet from unicode to ascii and make
            # text string lowercase for easier text analysis
            text = tweet['text'].encode('ascii', 'ignore').lower()

            source = source_regex.sub('', tweet['source'])

            #			print source

            #			text = str_in_quotations_regex.sub('', text)
            #			print tweet['id_str'] + ' ' + text
            #			if tweet['quoted_status_id'] != None: print tweet['quoted_status_id_str']
            #			print tweet['source'] + '\n'

            if get_filtered_keywords:
                # Pass text attribute to the compiled regex string and tokenize string
                tokens.extend(regexp_tokenize(text, regex, gaps=False))
                # Store only unique words
                filtered_tokens = [term for term in tokens if not term in stop_words]

            else:
                # Insert keyword into stop words
                stop_words.append(keyword)
                temp_tokens = regexp_tokenize(text, regex, gaps=False)

                # Only consider the keyword frequencies of tweets that contain the keyword
                if keyword in temp_tokens:
                    tokens.extend(regexp_tokenize(text, regex, gaps=False))
                    filtered_tokens = [term for term in tokens if not term in stop_words]
                    keyword_count += 1

                #					print tweet['id_str'] + ' ' + tweet['user']['screen_name'] + ': ' + tweet['text'] + ' ' + str(tweet['created_at']) + tweet['source']

            final_filtered_tokens.extend(filtered_tokens)
            if not get_filtered_keywords:
                del temp_tokens[:]
            del tokens[:]
            del filtered_tokens[:]

            # Update progress bar
            progress_bar_tokens.update(count + 1)
            count += 1

        except CursorNotFound:
            pass

    token_cursor.close()
    progress_bar_tokens.finish()

    return final_filtered_tokens


def write_tokens(tokens, filename):
    write_filename = filename + '.txt'
    with open(write_filename, 'w') as outfile:
        #	j = json.loads(tokens)
        json.dump(tokens, outfile)

    print 'Filtered tokens written to ' + write_filename
    return write_filename


def read_tokens(filename):
    f = open(filename, 'r')
    outfile = f.read()
    outfile = eval(outfile)
    # print outfile
    return outfile


def merge_collections(collection_to_copy, collection_to_insert):
    count = 0
    cursor = collection_to_copy.find()
    num_tweets_to_insert = collection_to_copy.count()

    widgets = ['Merging collections: ', Percentage(), ' ', Bar(marker=AnimatedMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]

    print str(collection_to_insert) + ' has ' + str(collection_to_insert.count()) + ' documents'

    progress_bar = ProgressBar(widgets=widgets, maxval=num_tweets_to_insert).start()

    for tweet in cursor:
        try:
            collection_to_insert.insert(tweet)
            progress_bar.update(count + 1)
            count += 1
        except CursorNotFound:
            pass

    progress_bar.finish()
    print 'Inserted ' + str(count) + ' documents'
    print str(collection_to_insert) + ' now has ' + str(collection_to_insert.count()) + ' documents'


def get_monograms_freqdist(tokens):
    freq_dist = FreqDist(tokens)
    # print FreqDist.N(freq_dist)
    print 'Returned monograms'

    print freq_dist.most_common(10)
    temp_list = freq_dist.most_common(100)
    temp_dict = dict((item[0], item[1]) for item in temp_list)
    ordered_freq_dist = OrderedDict(sorted(temp_dict.items(), key=lambda x: x[1], reverse=True))

    return ordered_freq_dist


def get_bigrams_freqdist(tokens):
    bi_grams = bigrams(tokens)
    print 'Returned bigrams'

    freq_dist_bigrams = FreqDist(bi_grams)

    print freq_dist_bigrams.most_common(10)

    freq_dist_bigrams_new = dict()
    for item in freq_dist_bigrams.items():
        temp_str = item[0]
        temp_key = temp_str[0] + ' ' + temp_str[1]
        freq_dist_bigrams_new[temp_key] = item[1]
    freq_dist_bigrams_new = OrderedDict(sorted(freq_dist_bigrams_new.items(), key=lambda x: x[1], reverse=True))
    # print freq_dist_bigrams_new

    return freq_dist_bigrams_new


def get_trigrams_freqdist(tokens):
    tri_grams = trigrams(tokens)
    print 'Returned trigrams'

    freq_dist_trigrams = FreqDist(tri_grams)
    print freq_dist_trigrams.most_common(10)

    freq_dist_trigrams_new = dict()
    for item in freq_dist_trigrams.items():
        temp_str = item[0]
        temp_key = temp_str[0] + ' ' + temp_str[1] + ' ' + temp_str[2]
        freq_dist_trigrams_new[temp_key] = item[1]
    freq_dist_trigrams_new = OrderedDict(sorted(freq_dist_trigrams_new.items(), key=lambda x: x[1], reverse=True))

    return freq_dist_trigrams_new


def get_keyword_times_series(query, keyword, num_tweets, collection):
    count = 0
    key_time_list = []

    cursor = collection.find(query, no_cursor_timeout=True, batch_size=75)

    # Command line progress bar init
    widgets = ['Word frequency series: ', keyword[:10], ' ', Percentage(), ' ', Bar(marker=AnimatedMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]

    progress_bar = ProgressBar(widgets=widgets, maxval=num_tweets).start()

    for tweet in cursor.limit(num_tweets):
        try:
            # Convert text attribute of tweet from unicode to ascii and make
            # text string lowercase for easier text analysis
            text = tweet['text'].encode('ascii', 'ignore').lower()

            if keyword in text:
                created_at = tweet['created_at'].encode('ascii', 'ignore')
                # print str(time)
                epoch = datetime(1970, 1, 1).second
                time_series = time.mktime(time.strptime(created_at, "%a %b %d %H:%M:%S +0000 %Y"))
                delta_t = (time_series - epoch)
                key_time_list.append(tweet['created_at'])

            # Update progress bar
            progress_bar.update(count + 1)
            count += 1

        except CursorNotFound:
            pass

    progress_bar.finish()
    cursor.close()

    # Create a list of ones that map to the number of keyword occurences
    key_time_ones = [1] * len(key_time_list)

    # Establish index to plot on x-axis
    key_time_idx = pandas.DatetimeIndex(key_time_list)

    # Create a series and refactor data to sum each occurrence in a one-minute span
    key_time_series = pandas.Series(key_time_ones, index=key_time_idx).resample('1Min', how='sum').fillna(0)

    return key_time_series


def get_interactive_plot(query, keyword, num_tweets, collection):
    count = 0
    key_time_list = []

    cursor = collection.find(query, no_cursor_timeout=True, batch_size=75)

    # Command line progress bar init
    widgets = ['Word frequency series: ', keyword[:10], ' ', Percentage(), ' ', Bar(marker=AnimatedMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]

    progress_bar = ProgressBar(widgets=widgets, maxval=num_tweets).start()

    for tweet in cursor.limit(num_tweets):
        try:
            # Convert text attribute of tweet from unicode to ascii and make
            # text string lowercase for easier text analysis
            text = tweet['text'].encode('ascii', 'ignore').lower()

            if keyword in text:
                key_time_list.append(tweet['created_at'])

            # Create a list of ones that map to the number of keyword occurences
            key_time_ones = [1] * len(key_time_list)

            # Establish index to plot on x-axis
            key_time_idx = pandas.DatetimeIndex(key_time_list)

            # Create a series and refactor data to sum each occurrence in a one-minute span
            key_time_series = pandas.Series(key_time_ones, index=key_time_idx).resample('1Min', how='sum').fillna(0)

            # Update progress bar
            progress_bar.update(count + 1)
            count += 1

        except CursorNotFound:
            pass

    progress_bar.finish()
    cursor.close()

    return key_time_series


# TODO: DataFrame Series
def get_dataframe_dict(freq_dict, num_words, query, num_tweets, collection):
    temp_list = []
    temp_dict = {}
    time_series = []
    i = 0

    for key in freq_dict.iterkeys():
        if i == num_words:
            break

        temp_series = get_keyword_times_series(query, key, num_tweets, collection)
        temp_dict.setdefault(key, temp_series)
        temp_list.append(key)
        time_series.append(temp_series)

        i += 1

    df = pandas.DataFrame(temp_dict).resample('1Min', how='sum').fillna(0)

    return df, time_series, temp_series


# TODO: finish obtaining location info in tweets
def get_mapping_info(query, num_tweets, collection):
    count = 0

    cursor = collection.find(query, no_cursor_timeout=True, batch_size=75)

    widgets = ['Tweet coordinates info: ', Percentage(), ' ', Bar(marker=AnimatedMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    progress_bar = ProgressBar(widgets=widgets, maxval=num_tweets).start()

    for tweet in cursor.limit(num_tweets):
        try:
            if tweet['coordinates'] is not None:
                print tweet['coordinates']['coordinates'][0]
        except CursorNotFound:
            pass

        progress_bar.update(count + 1)
        count += 1

    progress_bar.finish()
    cursor.close()


def main():
    #	tokens = read_tokens('wacoshootout3_6hrs_tokens.txt')
    #	bigrams_freqdist = get_bigrams_freqdist(tokens)
    # sm12hrs_bigrams = get_bigrams_freqdist(read_tokens('sm12hrs_tokens.txt'))
    # Regex string to parse emoticons
    emoticons_str = r"""
		(?:
			[:=;] # Eyes
			[oO\-]? # Nose (optional)
			[D\)\]\(\]/\\OpP] # Mouth
		)"""

    # Regex string to parse HTML tags, @-mentions, hashtags, URLs, numbers, etc.
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

    # Compile regex strings together
    tokens_regex = re.compile(r'(' + '|'.join(regex_str) + ')', re.VERBOSE | re.IGNORECASE)

    # Accumulate a list of punctuations, common (stop) words, and other common words
    # so that the word frequencies output unique words
    punctuation = list(string.punctuation)
    stop = stopwords.words('english') + punctuation + ['rt', 'via', 'san', 'marcos', 'river']

    # Initialize MongoDB collection to extract data from
    client = MongoClient()
    db = client.tweets
    # bill_collection = db.bill_words
    # flood_collection = db.flood
    charleston_collection = db.charleston_unique
    sm_flood_collection = db.sanmarcosflood
    waco_shootout_4_6hrs = db.wacoshootout_original4_6hrs
    waco_shootout_4 = db.wacoshootout_original4_12hrs
    waco_shootout_3_6hrs = db.wacoshootout_original3_6hrs
    waco_shootout_3_6hrs_test = db.wacoshootout_original3_6hrs_test
    wacoshootout_6hrs = db.wacoshootout_original_6hrs
    sm_flood_36hrs = db.sanmarcos36hrs
    sm_flood_12hrs = db.sanmarcos12hrs
    sm_flood_6hrs = db.sanmarcos6hrs
    sm_flood_3hrs = db.sanmarcos3hrs
    lafayette_12hrs = db.lafayette_shooting_unique

    # Max number of tweets to parse
    wacoshootout_6hrs_tweets = wacoshootout_6hrs.count()
    waco_shootout_4_tweets = waco_shootout_4.count()
    waco_shootout_4_6hrs_tweets = waco_shootout_4_6hrs.count()
    waco6hrs_tweets = waco_shootout_3_6hrs.count()
    max_tweets = sm_flood_collection.count()
    flood_tweets = 1000
    charleston_tweets = charleston_collection.count()
    sm_tweets = sm_flood_36hrs.count()
    sm12hrs_tweets = sm_flood_12hrs.count()
    sm6hrs_tweets = sm_flood_6hrs.count()
    sm3hrs_tweets = sm_flood_3hrs.count()
    lafayette_12hrs_tweets = lafayette_12hrs.count()

    # Number of tweets to iterate for frequency vs time plot
    collection_tweets = 1000

    # Start and end dates
    start_date = parse('2015-07-24T01:00:00Z')
    end_date = parse('2015-07-24T13:00:00Z')

    # Pymongo find() query
    date_filter = {'$and': [{'retweeted': False}, {'in_reply_to_status_id': None}, {'in_reply_to_user_id': None},
                            {'created_at': {'$gte': start_date, '$lt': end_date}}, {'retweeted_status': None}]}
    date = {'created_at': {'$gte': start_date, '$lt': end_date}}
    no_filter = {}
    retweet_filter = {'retweeted_status': None}

    #	print waco_shootout_4_tweets

    #	wacoshootout4 = parse_tweets(no_filter, tokens_regex, stop, waco_shootout_4_tweets, waco_shootout_4, True, '', db.wacoshootout4_freqdist)

    # merge_collections(waco_shootout_4_6hrs, waco_shootout_3_6hrs_test)

    print "Number of tweets: " + str(lafayette_12hrs_tweets) + '\n'
    # test_parse = parse_tweets(date, tokens_regex, stop, lafayette_12hrs_tweets, lafayette_12hrs, True, '')
    # write_tokens(test_parse, 'lafayette_12hrs_tokens')
    test_parse = read_tokens('lafayette_12hrs_tokens.txt')
    lafayette_12hrs_monograms = get_monograms_freqdist(test_parse)
    lafayette_12hrs_monograms_data = get_dataframe_dict(lafayette_12hrs_monograms, 5, date, lafayette_12hrs_tweets,
                                                        lafayette_12hrs)
    lafayette_12hrs_monograms_df = lafayette_12hrs_monograms_data[0]
    lafayette_12hrs_monograms_time = lafayette_12hrs_monograms_data[1]
    lafayette_time = lafayette_12hrs_monograms_data[2]

    axes = lafayette_12hrs_monograms_df.plot(figsize=(14, 4), colormap='spectral')
    axes.set_title("Lafayette Shooting Monograms (12 hrs)", fontsize=18)
    axes.set_xlabel("Time (UTC)")
    axes.set_ylabel("Freq")
    plt.show(axes)

    labels = list(lafayette_12hrs_monograms_df.columns.values)
    values = lafayette_12hrs_monograms_time
    time_values = lafayette_time.index.values
    print lafayette_12hrs_monograms_df
    print lafayette_time.index.values
    print lafayette_12hrs_monograms_time[1].values

    # plt.ion()
    # plt.axis('auto')
    # plt.set_cmap('spectral')
    # plt.show(False)

    # labels_index = 0
    # labels_dict = dict()
    #
    # for index in range(len(labels)):
    # 	labels_dict[labels[index]] = lafayette_12hrs_monograms_time[index].values
    #
    # print labels_dict

    # TODO: FIX LINE PLOTTING AND MULTIPLE PLOTS
    # if plt.isinteractive():
    # 	for i in range(len(time_values)):
    # 		for ii in range(len(labels)):
    # 			y = values[ii].values[i]
    # 			plt.plot(time_values[i], y, antialiased=False)
    # 		# plt.draw()
    # 		plt.pause(0.1)
    # 		# plt.draw()
    #
    # plt.show()

    for i in range(len(labels)):
        tooltip = mpld3.plugins.LineLabelTooltip(axes.get_lines()[i], labels[i])
        mpld3.plugins.connect(plt.gcf(), tooltip)

    mpld3.show()

# lafayette_12hrs_monograms_plot = vincent.Line(lafayette_12hrs_monograms_df[lafayette_12hrs_monograms_items])
# lafayette_12hrs_monograms_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_12hrs_monograms_plot.legend('Lafayette Shooting Monograms (12 hrs)')
# lafayette_12hrs_monograms_plot.to_json('lafayette_12hrs_monograms.json', html_out=True, html_path='lafayette_12hrs_monograms.html')
#
# lafayette_12hrs_bigrams = get_bigrams_freqdist(test_parse)
# lafayette_12hrs_bigrams_data = get_dataframe_dict(lafayette_12hrs_bigrams, 10, date, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_12hrs_bigrams_df = lafayette_12hrs_bigrams_data[0]
# lafayette_12hrs_bigrams_items = lafayette_12hrs_bigrams_data[1]
# lafayette_12hrs_bigrams_plot = vincent.Line(lafayette_12hrs_bigrams_df[lafayette_12hrs_bigrams_items])
# lafayette_12hrs_bigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_12hrs_bigrams_plot.legend('Lafayette Shooting bigrams (12 hrs)')
# lafayette_12hrs_bigrams_plot.to_json('lafayette_12hrs_bigrams.json', html_out=True, html_path='lafayette_12hrs_bigrams.html')
#
# lafayette_12hrs_trigrams = get_trigrams_freqdist(test_parse)
# lafayette_12hrs_trigrams_data = get_dataframe_dict(lafayette_12hrs_trigrams, 10, date, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_12hrs_trigrams_df = lafayette_12hrs_trigrams_data[0]
# lafayette_12hrs_trigrams_items = lafayette_12hrs_trigrams_data[1]
# lafayette_12hrs_trigrams_plot = vincent.Line(lafayette_12hrs_trigrams_df[lafayette_12hrs_trigrams_items])
# lafayette_12hrs_trigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_12hrs_trigrams_plot.legend('Lafayette Shooting trigrams (12 hrs)')
# lafayette_12hrs_trigrams_plot.to_json('lafayette_12hrs_trigrams.json', html_out=True, html_path='lafayette_12hrs_trigrams.html')
#
# start_date1 = parse('2015-07-24T01:00:00Z')
# end_date1 = parse('2015-07-24T07:00:00Z')
# date1 = {'created_at': {'$gte': start_date1, '$lt': end_date1}}
#
# test_parse = parse_tweets(date1, tokens_regex, stop, lafayette_12hrs_tweets, lafayette_12hrs, True, '')
# write_tokens(test_parse, 'lafayette_6hrs_tokens')
# lafayette_6hrs_monograms = get_monograms_freqdist(test_parse)
# lafayette_6hrs_monograms_data = get_dataframe_dict(lafayette_6hrs_monograms, 10, date1, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_6hrs_monograms_df = lafayette_6hrs_monograms_data[0]
# lafayette_6hrs_monograms_items = lafayette_6hrs_monograms_data[1]
# lafayette_6hrs_monograms_plot = vincent.Line(lafayette_6hrs_monograms_df[lafayette_6hrs_monograms_items])
# lafayette_6hrs_monograms_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_6hrs_monograms_plot.legend('Lafayette Shooting Monograms (6 hrs)')
# lafayette_6hrs_monograms_plot.to_json('lafayette_6hrs_monograms.json', html_out=True, html_path='lafayette_6hrs_monograms.html')
#
# lafayette_6hrs_bigrams = get_bigrams_freqdist(test_parse)
# lafayette_6hrs_bigrams_data = get_dataframe_dict(lafayette_6hrs_bigrams, 10, date1, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_6hrs_bigrams_df = lafayette_6hrs_bigrams_data[0]
# lafayette_6hrs_bigrams_items = lafayette_6hrs_bigrams_data[1]
# lafayette_6hrs_bigrams_plot = vincent.Line(lafayette_6hrs_bigrams_df[lafayette_6hrs_bigrams_items])
# lafayette_6hrs_bigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_6hrs_bigrams_plot.legend('Lafayette Shooting bigrams (6 hrs)')
# lafayette_6hrs_bigrams_plot.to_json('lafayette_6hrs_bigrams.json', html_out=True, html_path='lafayette_6hrs_bigrams.html')
#
# lafayette_6hrs_trigrams = get_trigrams_freqdist(test_parse)
# lafayette_6hrs_trigrams_data = get_dataframe_dict(lafayette_6hrs_trigrams, 10, date1, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_6hrs_trigrams_df = lafayette_6hrs_trigrams_data[0]
# lafayette_6hrs_trigrams_items = lafayette_6hrs_trigrams_data[1]
# lafayette_6hrs_trigrams_plot = vincent.Line(lafayette_6hrs_trigrams_df[lafayette_6hrs_trigrams_items])
# lafayette_6hrs_trigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_6hrs_trigrams_plot.legend('Lafayette Shooting trigrams (6 hrs)')
# lafayette_6hrs_trigrams_plot.to_json('lafayette_6hrs_trigrams.json', html_out=True, html_path='lafayette_6hrs_trigrams.html')
#
# start_date2 = parse('2015-07-24T01:00:00Z')
# end_date2 = parse('2015-07-24T04:00:00Z')
# date2 = {'created_at': {'$gte': start_date2, '$lt': end_date2}}
#
# test_parse = parse_tweets(date2, tokens_regex, stop, lafayette_12hrs_tweets, lafayette_12hrs, True, '')
# write_tokens(test_parse, 'lafayette_3hrs_tokens')
# lafayette_3hrs_monograms = get_monograms_freqdist(test_parse)
# lafayette_3hrs_monograms_data = get_dataframe_dict(lafayette_3hrs_monograms, 10, date2, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_3hrs_monograms_df = lafayette_3hrs_monograms_data[0]
# lafayette_3hrs_monograms_items = lafayette_3hrs_monograms_data[1]
# lafayette_3hrs_monograms_plot = vincent.Line(lafayette_3hrs_monograms_df[lafayette_3hrs_monograms_items])
# lafayette_3hrs_monograms_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_3hrs_monograms_plot.legend('Lafayette Shooting Monograms (3 hrs)')
# lafayette_3hrs_monograms_plot.to_json('lafayette_3hrs_monograms.json', html_out=True, html_path='lafayette_3hrs_monograms.html')
#
# lafayette_3hrs_bigrams = get_bigrams_freqdist(test_parse)
# lafayette_3hrs_bigrams_data = get_dataframe_dict(lafayette_3hrs_bigrams, 10, date2, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_3hrs_bigrams_df = lafayette_3hrs_bigrams_data[0]
# lafayette_3hrs_bigrams_items = lafayette_3hrs_bigrams_data[1]
# lafayette_3hrs_bigrams_plot = vincent.Line(lafayette_3hrs_bigrams_df[lafayette_3hrs_bigrams_items])
# lafayette_3hrs_bigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_3hrs_bigrams_plot.legend('Lafayette Shooting bigrams (3 hrs)')
# lafayette_3hrs_bigrams_plot.to_json('lafayette_3hrs_bigrams.json', html_out=True, html_path='lafayette_3hrs_bigrams.html')
#
# lafayette_3hrs_trigrams = get_trigrams_freqdist(test_parse)
# lafayette_3hrs_trigrams_data = get_dataframe_dict(lafayette_3hrs_trigrams, 10, date2, lafayette_12hrs_tweets, lafayette_12hrs)
# lafayette_3hrs_trigrams_df = lafayette_3hrs_trigrams_data[0]
# lafayette_3hrs_trigrams_items = lafayette_3hrs_trigrams_data[1]
# lafayette_3hrs_trigrams_plot = vincent.Line(lafayette_3hrs_trigrams_df[lafayette_3hrs_trigrams_items])
# lafayette_3hrs_trigrams_plot.axis_titles(x='Time (UTC)', y='Freq')
# lafayette_3hrs_trigrams_plot.legend('Lafayette Shooting trigrams (3 hrs)')
# lafayette_3hrs_trigrams_plot.to_json('lafayette_3hrs_trigrams.json', html_out=True, html_path='lafayette_3hrs_trigrams.html')

# get_monograms_freqdist(read_tokens('wacoshootout4_12hrs_tokens.txt'))

# wacoshootout4_12hrs_monograms = get_monograms_freqdist(read_tokens('wacoshootout4_12hrs_tokens.txt'))
# wacoshootout4_12hrs_monograms_data = get_dataframe_dict(wacoshootout4_12hrs_monograms, 10, no_filter, waco_shootout_4_tweets, waco_shootout_4)
# wacoshootout4_12hrs_monograms_df = wacoshootout4_12hrs_monograms_data[0]
# wacoshootout4_12hrs_monograms_items = wacoshootout4_12hrs_monograms_data[1]
# wacoshootout4_12hrs_monograms_plot = vincent.Line(wacoshootout4_12hrs_monograms_df[wacoshootout4_12hrs_monograms_items])
# wacoshootout4_12hrs_monograms_plot.axis_titles(x = 'Time (UTC)', y = 'Freq')
# wacoshootout4_12hrs_monograms_plot.legend(title = 'Wacoshootout (4) 12hrs monograms')
# wacoshootout4_12hrs_monograms_plot.to_json('wacoshootout4_12hrs_monograms.json', html_out = True, html_path = 'wacoshootout4_12hrs_monograms.html')
#
# wacoshootout4_12hrs_trigrams = get_trigrams_freqdist(read_tokens('wacoshootout4_12hrs_tokens.txt'))
# wacoshootout4_12hrs_trigrams_data = get_dataframe_dict(wacoshootout4_12hrs_trigrams, 10, no_filter, waco_shootout_4_tweets, waco_shootout_4)
# wacoshootout4_12hrs_trigrams_df = wacoshootout4_12hrs_trigrams_data[0]
# wacoshootout4_12hrs_trigrams_items = wacoshootout4_12hrs_trigrams_data[1]
# wacoshootout4_12hrs_trigrams_plot = vincent.Line(wacoshootout4_12hrs_trigrams_df[wacoshootout4_12hrs_trigrams_items])
# wacoshootout4_12hrs_trigrams_plot.axis_titles(x = 'Time (UTC)', y = 'Freq')
# wacoshootout4_12hrs_trigrams_plot.legend(title = 'Wacoshootout (4) 12hrs trigrams')
# wacoshootout4_12hrs_trigrams_plot.to_json('wacoshootout4_12hrs_trigrams.json', html_out = True, html_path = 'wacoshootout4_12hrs_trigrams.html')
# sm12hrs_monograms = get_monograms_freqdist(read_tokens('sm12hrs_tokens.txt'))
# sm12hrs_bigrams = get_bigrams_freqdist(read_tokens('sm12hrs_tokens.txt'))
# sm12hrs_bigrams_data = get_dataframe_dict(sm12hrs_bigrams, 10, no_filter, sm12hrs_tweets, sm_flood_12hrs)
# sm12hrs_bigrams_df = sm12hrs_bigrams_data[0]
# sm12hrs_bigrams_items = sm12hrs_bigrams_data[1]
# sm12hrs_bigrams_plot = vincent.Line(sm12hrs_bigrams_df[sm12hrs_bigrams_items])
# sm12hrs_bigrams_plot.axis_titles(x = 'Time (UTC', y = 'Freq')
# sm12hrs_bigrams_plot.legend(title = 'SM Flood 12Hrs (1am to 1pm) Bigrams')
# sm12hrs_bigrams_plot.to_json('sm12hrs_bigrams.json', html_out = True, html_path = 'sm12hrs_bigrams.html')
# sm12hrs_trigrams = get_trigrams_freqdist(read_tokens('sm12hrs_tokens.txt'))
# print 'Starting sentimental analysis on collection \'sanmarcos12hrs\': ' + str(waco_shootout_4_6hrs_tweets) + ' tweets'
# blanco_sm12hrs_tokens = parse_tweets(no_filter, tokens_regex, stop, sm12hrs_tweets, sm_flood_12hrs, False, 'blanco')
# write_tokens(blanco_sm12hrs_tokens, 'blanco_sm12hrs_tokens')
# blanco_sm12hrs_monograms = get_monograms_freqdist(blanco_sm12hrs_tokens)
# blanco_sm12hrs_bigrams = get_bigrams_freqdist(blanco_sm12hrs_tokens)
# blanco_sm12hrs_trigrams = get_trigrams_freqdist(blanco_sm12hrs_tokens)
# blanco_sm12hrs_monograms_data = get_dataframe_dict(blanco_sm12hrs_monograms, 10, no_filter, sm12hrs_tweets, sm_flood_12hrs)
# blanco_sm12hrs_monograms_df = blanco_sm12hrs_monograms_data[0]
# blanco_sm12hrs_monograms_items = blanco_sm12hrs_monograms_data[1]
# blanco_sm12hrs_monograms_plot = vincent.Line(blanco_sm12hrs_monograms_df[blanco_sm12hrs_monograms_items])
# blanco_sm12hrs_monograms_plot.axis_titles(x = 'Time (UTC)', y = 'Freq')
# blanco_sm12hrs_monograms_plot.legend(title = 'SM Flood Monograms 12hrs (1am - 1pm on May 24) with keyword: \'blanco\'')
# blanco_sm12hrs_monograms_plot.to_json('blanco_sm12hrs_monograms.json', html_out = True, html_path = 'blanco_sm12hrs_monograms.html')
#
# luling_sm12hrs_tokens = parse_tweets(no_filter, tokens_regex,stop, sm12hrs_tweets, sm_flood_12hrs, False, 'luling')
# write_tokens(luling_sm12hrs_tokens, 'luling_sm12hrs_tokens')
# luling_sm12hrs_monograms = get_monograms_freqdist(luling_sm12hrs_tokens)
# luling_sm12hrs_bigrams = get_bigrams_freqdist(luling_sm12hrs_tokens)
# luling_sm12hrs_trigrams = get_trigrams_freqdist(luling_sm12hrs_tokens)
# luling_sm12hrs_monograms_data = get_dataframe_dict(luling_sm12hrs_monograms, 10, no_filter, sm12hrs_tweets, sm_flood_12hrs)
# luling_sm12hrs_monograms_df = luling_sm12hrs_monograms_data[0]
# luling_sm12hrs_monograms_items = luling_sm12hrs_monograms_data[1]
# luling_sm12hrs_monograms_plot = vincent.Line(luling_sm12hrs_monograms_df[luling_sm12hrs_monograms_items])
# luling_sm12hrs_monograms_plot.axis_titles(x = 'Time (UTC)', y = 'Freq')
# luling_sm12hrs_monograms_plot.legend(title = 'SM Flood Monograms 12hrs (1am - 1pm on May 24) with keyword: \'luling\'')
# luling_sm12hrs_monograms_plot.to_json('luling_sm12hrs_monograms.json', html_out = True, html_path = 'luling_sm12hrs_monograms.html')
#	sm3hrs_tokens = parse_tweets(no_filter, tokens_regex, stop, sm3hrs_tweets, sm_flood_3hrs, True, '')

# # Location series
# houston_series = get_keyword_times_series(date_filter, 'houston', collection_tweets, bill_collection)
# matagorda_series = get_keyword_times_series(date_filter, 'matagorda', collection_tweets, bill_collection)
# austin_series = get_keyword_times_series(date_filter, 'austin', collection_tweets, bill_collection)

# keywords_dict = {'landfall' : landfall_series, 'coast' : coast_series, 'safe' : safe_series, 'stay' : stay_series, 'flooding' : flooding_series}
# location_dict = {'houston' : houston_series, 'matagorda' : matagorda_series, 'austin' : austin_series}

# keywords_df = pandas.DataFrame(keywords_dict).resample('1Min', how = 'sum').fillna(0)
# location_df = pandas.DataFrame(location_dict).resample('1Min', how = 'sum').fillna(0)

# keywords_time_chart = vincent.Line(keywords_df[['landfall', 'coast', 'safe', 'stay', 'flooding']])
# keywords_time_chart.axis_titles(x = 'Time (UTC)', y = 'Freq')
# keywords_time_chart.legend(title = 'Keywords')
# keywords_time_chart.to_json('bill_keywords_time_chart.json', html_out = True, html_path = 'bill_keywords.html')

# location_time_chart = vincent.Line(location_df[['houston', 'matagorda', 'austin']])
# location_time_chart.axis_titles(x = 'Time (UTC)', y = 'Freq')
# location_time_chart.legend(title = 'Locations')
# location_time_chart.to_json('bill_locations_time_chart.json', html_out = True, html_path = 'bill_locations.html')

# warning_series = get_keyword_times_series(no_filter, 'warning', collection_tweets, flood_collection)
# spot_series = get_keyword_times_series(no_filter, 'spot', collection_tweets, flood_collection)
# alert_series = get_keyword_times_series(no_filter, 'alert', collection_tweets, flood_collection)

# words = {'warning' : warning_series, 'spot' : spot_series, 'alert' : alert_series}

# words_df = pandas.DataFrame(words)
# words_df = words_df.resample('1Min').fillna(0)

# print words_df

# # time_chart = vincent.Line(words_df[['warning', 'spot', 'alert']])
# # time_chart.axis_titles(x = 'Time', y = 'Freq')
# # time_chart.legend(title = 'Keyword')
# # time_chart.to_json('flood_time_chart.json', html_out = True, html_path = 'flood_line.html')

# # get_mapping_info(no_filter, collection_tweets, flood_collection)

# # san_marcos_map = folium.Map(location = [29.890661, -97.911530], tiles = 'Stamen Toner', zoom_start = 13)
# # san_marcos_map.simple_marker([29.90, -98.0])
# # san_marcos_map.simple_marker([25.0, 65.0])
# # san_marcos_map.create_map(path = 'san_marcos_map.html')

# if __name__ == '__main__':
# 	main()
