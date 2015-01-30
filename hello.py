import os
from flask import request, Flask, render_template
from flask import redirect, url_for, session
from instagram.client import InstagramAPI
from collections import Counter
import numpy as np 
import pandas as pd
import simplejson, urllib

app = Flask(__name__)
app.debug = True
with open('flask.secret', 'r') as f:
    app.secret_key = f.read()
    
# CONFIG redirect change for production
# (also change on Instagram API)
with open('client_id.secret', 'r') as f:
    client_id = f.read()
with open('client_secret.secret', 'r') as f:
    client_secret = f.read()

CONFIG = {
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': 'http://insta-insights.herokuapp.com/oauth_callback'
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

@app.route('/oauth_callback')
def oauth_callback():
    code = request.args['code']
    access_token, user_info = unauthenticated_api.exchange_code_for_access_token(code)
    session['access_token'] = access_token 
    session['user_info'] = user_info
    return redirect(url_for('insights'))

@app.route('/insights')
def insights():
    user_info = session['user_info']
    api = InstagramAPI(access_token=session['access_token'])
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

    # isolate filters and likes into dataframe
    df_filter = pd.DataFrame({'filter' : np.array(filters),
        'likes': np.array(likes)})
    # group_by, summarize mean, and sort (re-list filters)
    mean_by_filter = df_filter.groupby('filter').agg([np.mean]).sort(
        [('likes', 'mean')], ascending=[0])
    mean_by_filter_list = mean_by_filter.iloc[:,0].tolist()
    filters = mean_by_filter.index.tolist()

    # isolate hours and likes into dataframe
    hours = [t.hour for t in times]
    missing_hours = []
    # add in hours that have 0 count
    filled_likes = list(likes)
    for i in range(0, 23):
        if i not in hours:
            missing_hours.append(i)
            hours.append(i)
            filled_likes.append(0)
    df_hour = pd.DataFrame({'hour' : np.array(hours),
        'likes' : np.array(filled_likes)})
    mean_by_hour = df_hour.groupby('hour').agg([np.mean, len])
    mean_by_hour_list = mean_by_hour.iloc[:,0].tolist()
    posts_by_hour_list = mean_by_hour.iloc[:, 1].tolist()
    # the missing ones need to be reset to 0 (counted as 1)
    for mhour in missing_hours:
        posts_by_hour_list[mhour] = 0

    ### captions
    num_words = []
    num_tags = []
    for p in media:
        if p.caption is not None:
            num_words.append(len(p.caption.text.split(' ')))
        else:
            num_words.append(0)
        if 'tags' in p.__dict__.keys():
            num_tags.append(len(p.tags))
        else:
            num_tags.append(0)
    # likes by words in caption
    df_caption = pd.DataFrame({'num_words' : np.array(num_words),
        'num_tags' : np.array(num_tags),
        'likes' : np.array(likes)})
    mean_by_words = df_caption.groupby('num_words').agg(np.mean)
    mean_by_words_list = mean_by_words.iloc[:,0].tolist()
    mean_by_words_labels = [int(i) for i in mean_by_words.index.tolist()]
    mean_by_tags = df_caption.groupby('num_tags').agg(np.mean)
    mean_by_tags_list = mean_by_tags.iloc[:, 0].tolist()
    mean_by_tags_labels = [int(i) for i in mean_by_tags.index.tolist()]

    ### embarassing
    # number of your own pictures you liked
    sad_count = 0
    for p in media:
        if (p.user_has_liked):
            sad_count += 1

    # count number of #nofilter with filters
    false_nofilter_count = 0
    true_nofilter_count = 0

    for p in media:
        # check if there is actually no filter
        if p.filter != 'Normal':
            # check if there is a #nofilter hashtag     
            if 'tags' in p.__dict__.keys():
                if 'nofilter' in [t.name.lower() for t in p.tags]:
                    false_nofilter_count += 1
        else:
            # check if there is a #nofilter hashtag     
            if 'tags' in p.__dict__.keys():
                if 'nofilter' in [t.name.lower() for t in p.tags]:
                    true_nofilter_count += 1

    ### biggest fans
    fans = {}
    pic_urls = {}
    for p in media:
        url = 'https://api.instagram.com/v1/media/' + str(p.id) +'/likes?access_token=' + access_token
        result = simplejson.load(urllib.urlopen(url))
        for u in result['data']:
            username = u['username']
            pic_url = u['profile_picture']
            if username not in fans.keys():
                fans[username] = 1
                pic_urls[username] = pic_url
            else:
                fans[username] = fans[username] + 1
    df = pd.DataFrame.from_dict(fans, orient='index')
    df.columns = ['posts_liked']
    df = df.sort('posts_liked', ascending=0)

    # top 5 + prof pics
    top_fans = []
    for fan in df.iloc[0:6, 0].index:
        top_fans.append({'username': fan,
            'likes': int(df.loc[fan]),
            'prof_pic': pic_urls[fan]})


    return render_template('insights.html',
        username=user_info['username'],
        likes=likes,
        times=times,
        blank_times=[""]*len(times),
        filter_counts = filter_data,
        type_counts = types_data,
        filters = filters,
        filter_likes = mean_by_filter_list,
        hours = range(0, 24),
        hour_likes = mean_by_hour_list,
        hour_posts = posts_by_hour_list,
        words = mean_by_words_labels,
        word_likes = mean_by_words_list,
        tags = mean_by_tags_labels,
        tag_likes = mean_by_tags_list,
        sad_count = sad_count,
        false_nofilter_count=false_nofilter_count,
        true_nofilter_count=true_nofilter_count,
        total_nofilter_count=false_nofilter_count+true_nofilter_count,
        top_fans=top_fans)

# testing for myself
@app.route('/eddie')
def eddie():
    # dict so i can c&p into the real view above
    user_info = {'username': 'edz504'}
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

    # isolate filters and likes into dataframe
    df_filter = pd.DataFrame({'filter' : np.array(filters),
        'likes': np.array(likes)})
    # group_by, summarize mean, and sort (re-list filters)
    mean_by_filter = df_filter.groupby('filter').agg([np.mean]).sort(
        [('likes', 'mean')], ascending=[0])
    mean_by_filter_list = mean_by_filter.iloc[:,0].tolist()
    filters = mean_by_filter.index.tolist()

    # isolate hours and likes into dataframe
    hours = [t.hour for t in times]
    missing_hours = []
    # add in hours that have 0 count
    filled_likes = list(likes)
    for i in range(0, 23):
        if i not in hours:
            missing_hours.append(i)
            hours.append(i)
            filled_likes.append(0)
    df_hour = pd.DataFrame({'hour' : np.array(hours),
        'likes' : np.array(filled_likes)})
    mean_by_hour = df_hour.groupby('hour').agg([np.mean, len])
    mean_by_hour_list = mean_by_hour.iloc[:,0].tolist()
    posts_by_hour_list = mean_by_hour.iloc[:, 1].tolist()
    # the missing ones need to be reset to 0 (counted as 1)
    for mhour in missing_hours:
        posts_by_hour_list[mhour] = 0

    ### captions
    num_words = []
    num_tags = []
    for p in media:
        if p.caption is not None:
            num_words.append(len(p.caption.text.split(' ')))
        else:
            num_words.append(0)
        if 'tags' in p.__dict__.keys():
            num_tags.append(len(p.tags))
        else:
            num_tags.append(0)
    # likes by words in caption
    df_caption = pd.DataFrame({'num_words' : np.array(num_words),
        'num_tags' : np.array(num_tags),
        'likes' : np.array(likes)})
    mean_by_words = df_caption.groupby('num_words').agg(np.mean)
    mean_by_words_list = mean_by_words.iloc[:,0].tolist()
    mean_by_words_labels = [int(i) for i in mean_by_words.index.tolist()]
    mean_by_tags = df_caption.groupby('num_tags').agg(np.mean)
    mean_by_tags_list = mean_by_tags.iloc[:, 0].tolist()
    mean_by_tags_labels = [int(i) for i in mean_by_tags.index.tolist()]

    ### embarassing
    # number of your own pictures you liked
    sad_count = 0
    for p in media:
        if (p.user_has_liked):
            sad_count += 1

    # count number of #nofilter with filters
    false_nofilter_count = 0
    true_nofilter_count = 0

    for p in media:
        # check if there is actually no filter
        if p.filter != 'Normal':
            # check if there is a #nofilter hashtag     
            if 'tags' in p.__dict__.keys():
                if 'nofilter' in [t.name.lower() for t in p.tags]:
                    false_nofilter_count += 1
        else:
            # check if there is a #nofilter hashtag     
            if 'tags' in p.__dict__.keys():
                if 'nofilter' in [t.name.lower() for t in p.tags]:
                    true_nofilter_count += 1

    ### biggest fans
    fans = {}
    pic_urls = {}
    for p in media:
        url = 'https://api.instagram.com/v1/media/' + str(p.id) +'/likes?access_token=' + access_token
        result = simplejson.load(urllib.urlopen(url))
        for u in result['data']:
            username = u['username']
            pic_url = u['profile_picture']
            if username not in fans.keys():
                fans[username] = 1
                pic_urls[username] = pic_url
            else:
                fans[username] = fans[username] + 1
    df = pd.DataFrame.from_dict(fans, orient='index')
    df.columns = ['posts_liked']
    df = df.sort('posts_liked', ascending=0)

    # top 5 + prof pics
    top_fans = []
    for fan in df.iloc[0:6, 0].index:
        top_fans.append({'username': fan,
            'likes': int(df.loc[fan]),
            'prof_pic': pic_urls[fan]})


    return render_template('insights.html',
        username=user_info['username'],
        likes=likes,
        times=times,
        blank_times=[""]*len(times),
        filter_counts = filter_data,
        type_counts = types_data,
        filters = filters,
        filter_likes = mean_by_filter_list,
        hours = range(0, 24),
        hour_likes = mean_by_hour_list,
        hour_posts = posts_by_hour_list,
        words = mean_by_words_labels,
        word_likes = mean_by_words_list,
        tags = mean_by_tags_labels,
        tag_likes = mean_by_tags_list,
        sad_count = sad_count,
        false_nofilter_count=false_nofilter_count,
        true_nofilter_count=true_nofilter_count,
        total_nofilter_count=false_nofilter_count+true_nofilter_count,
        top_fans=top_fans)

if __name__ == '__main__':
    app.run()