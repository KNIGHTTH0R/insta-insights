import os
from flask import request
from flask import Flask
from flask import render_template
from instagram.client import InstagramAPI

app = Flask(__name__)
app.debug = True

# CONFIG redirect change for production
# (also change on Instagram API)

CONFIG = {
    'client_id': '15f6735cc27f4e51820653e4ab91bfae',
    'client_secret': 'a4baf8708e504915a8d2f0bf2f9a3bba',
    'redirect_uri': 'http://insta-like-insights.herokuapp.com/insights'
}

unauthenticated_api = InstagramAPI(**CONFIG)

@app.route('/')
def landing():
    url = unauthenticated_api.get_authorize_url()
    return render_template('cover.html',
        url=url)

@app.route('/insights')
def eddie():
    code = request.args['code']
    access_token, user_info = unauthenticated_api.exchange_code_for_access_token(code)
    # return str(user_info.keys())
    api = InstagramAPI(access_token=access_token)
    recent_media, next_ = api.user_recent_media()
    likes = [p.like_count for p in recent_media]
    times = [p.created_time for p in recent_media]
    while next_:
        more_media, next_ = api.user_recent_media(with_next_url=next_)
        likes.extend(p.like_count for p in more_media)
        times.extend(p.created_time for p in more_media)

    likes.reverse() # returned in recent order
    times.reverse()

    return render_template('test_chartjs.html',
        username=user_info['username'],
        likes=likes,
        times=range(0, len(times)))

# below is for development only (when running python hello.py)
if __name__ == '__main__':
    app.run()