from django.db import models
from mongoengine import *
# Create your models here.

from TweetFreq.settings import DBNAME

class Search(Document):
    keywords = StringField()
