# LMI Twitter Project

## Setup
### Twitter Stream (Node.js)

1. [Create a Pusher Account] (https://pusher.com/signup)
2. [Create a Twitter application] (https://apps.twitter.com/)
3. `cd stream`
4. Generate access tokens on the "Keys and Access Tokens" tab
5. Copy `config.example.js` to a new file named `config.js`
6. Fill `config.js` with the keys from Pusher and Twitter and keywords
7. Install dependencies by running `npm install`
8. Test API locally by running `node index.js` and check [API endpoint] (http://localhost:5001/keywords.json)
9. Upload to Heroku 

### Django Project

1. Make sure you have [`virtualenv`] (https://virtualenv.readthedocs.org/en/latest/) and [Mongodb] (https://docs.mongodb.org/v2.6/installation/) installed.
2. `cd tweetcaster`
3. Create a new virtual environment via `virtualenv venv`
4. Activate virtual environment with `source venv/bin/activate`
5. Install dependencies with `pip install -r requirements.txt` (This may take a few minutes)
6. Navigate to `wordstream/views.py` and fill in the values for the Twitter Application keys and Pusher keys
7. To manage the MongoDB setup, change the value of `db` to `client.<db_name>` and `collection` to `db.<collection_name>`
8. Run `python manage.py migrate` and ensure no errors come up.
9. To run locally, type `python manage.py runserver` and navigate to the [index page] (http://localhost:8000/wordstream/)
10. Note that it does not take the `POST` request from the keyword form to the Twitter stream handler if running the application locally. To have the form submit the keywords to the stream API endpoint on Heroku, host the Django application on Heroku. Then navigate to `stream/index.js` to make the following modifications:
    * Replace all instances of `'http://localhost:8000/wordstream/static/js/config.js';` with `'https://<heroku_app_name>.herokuapp.com/static/js/config.js';`
    * Replace `http.get(file_url, function(response)` with `https.get(file_url, function(response)` on `line 49`
    * Replace `http.get('http://localhost:8000/wordstream/static/js/submit.json', function(response)` with `https.get('https://<heroku_app_name>.herokuapp.com/static/js/submit.json', function(response)` on `line 64`

