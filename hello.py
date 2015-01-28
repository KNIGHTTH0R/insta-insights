import os
from flask import Flask
from flask import render_template
from instagram.client import InstagramAPI

app = Flask(__name__)
app.debug = True

# @app.route('/')
# def landing():
#     return render_template('')

@app.route('/')
def eddie():
    with open('my_token.data', 'r') as f:
        acc_token = f.read()
    api = InstagramAPI(access_token=acc_token)
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
        username='edz504',
        likes=likes,
        times=range(0, len(times)))
    # return 'Hello'

@app.route('/test')
def test():
    return render_template('cover.html')

# below is for development only (when running python hello.py)
if __name__ == '__main__':
    app.run()