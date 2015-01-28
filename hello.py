import os
from flask import request
from flask import Flask
from flask import render_template
from instagram.client import InstagramAPI
from collections import Counter

app = Flask(__name__)
app.debug = True

# CONFIG redirect change for production
# (also change on Instagram API)

CONFIG = {
    'client_id': '15f6735cc27f4e51820653e4ab91bfae',
    'client_secret': 'a4baf8708e504915a8d2f0bf2f9a3bba',
    'redirect_uri': 'http://insta-insights.herokuapp.com/insights'
}

colors = ['#1abc9c', '#3498db', '#34495e', '#27ae60', '#8e44ad',
    '#f1c40f', '#e74c3c', '#95a5a6', '#d35400', '#bdc3c7', 
    '#2ecc71', '#9b59b6', '#16a085', '#2980b9', '#2c3e50',
    '#e67e22', '#ecf0f1', '#f39c12', '#c0392b', '#7f8c8d']

unauthenticated_api = InstagramAPI(**CONFIG)

# color scaling from 
# http://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html
def color_variant(hex_color, brightness_offset=1):  
    """ takes a color like #87c95f and produces a lighter or darker variant """  
    if len(hex_color) != 7:  
        raise Exception("Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)  
    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]  
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]  
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int] # make sure new values are between 0 and 255  
    # hex() produces "0x88", we want just "88"  
    return "#" + "".join([hex(i)[2:] for i in new_rgb_int])  


@app.route('/')
def landing():
    url = unauthenticated_api.get_authorize_url()
    return render_template('cover.html',
        url=url)

@app.route('/insights')
def insights():
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

    return render_template('insights.html',
        username=user_info['username'],
        likes=likes,
        times=range(0, len(times)))

# testing for myself
@app.route('/eddie')
def eddie():
    with open('my_token.data', 'r') as f:
        access_token = f.read()
    api = InstagramAPI(access_token=access_token)
    recent_media, next_ = api.user_recent_media()
    ### get all media in one list
    media = [p for p in recent_media]
    while next_:
        m_media, next_ = api.user_recent_media(with_next_url=next_)
        media.extend(p for p in m_media)

    media.reverse() # returned in recent order

    likes = [p.like_count for p in media]
    times = [p.created_time for p in media]
    filters = [p.filter for p in media]
    types = [p.type for p in media]

    # manipulate filters and types into dictionary (data format for Chart.js)
    filter_counts = Counter(filters)
    types_counts = Counter(types)

    filter_data = []
    for i in range(0, len(filter_counts.keys())):
        this_filter = filter_counts.keys()[i]
        filter_data.append({'label': this_filter, 'value': filter_counts[this_filter], 'color': colors[i], 'highlight': color_variant(colors[i], brightness_offset=50)})
    types_data = []
    for i in range(0, len(types_counts.keys())):
        this_types = types_counts.keys()[i]
        types_data.append({'label': this_types, 'value': types_counts[this_types], 'color': colors[i], 'highlight': color_variant(colors[i], brightness_offset=50)})

    return render_template('insights.html',
        username='edz504',
        likes=likes,
        times=times,
        blank_times=[""]*len(times),
        filters=filter_data,
        types=types_data)

# below is for development only (when running python hello.py)
if __name__ == '__main__':
    app.run()