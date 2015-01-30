from instagram.client import InstagramAPI

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
pic1 = media[0]

# it seems media.likes only ever returns 4 users.  trying with url?
import simplejson, urllib, psycopg2, os, urlparse
url1 = 'https://api.instagram.com/v1/media/' + str(pic1.id) +'/likes?access_token=' + access_token
result = simplejson.load(urllib.urlopen(url1))
usernames = [u['username'] for u in result['data']]

################
# captions

# words in caption
caption_word_count = {}
for p in media:
    if p.caption is not None:
        this_word_count = len(p.caption.text.split(' '))
        if this_word_count not in caption_word_count.keys():
            caption_word_count[this_word_count] = 1
        else:
            caption_word_count[this_word_count] += 1

# tags in caption
caption_tag_count = {}
for p in media:
    if 'tags' in p.__dict__.keys():
        this_tag_count = len(p.tags)
        if this_tag_count not in caption_tag_count.keys():
            caption_tag_count[this_tag_count] = 1
        else:
            caption_tag_count[this_tag_count] += 1

################

################
# embarassing

# number of your own pictures you liked
sad_count = 0
for p in media:
    if (p.user_has_liked):
        sad_count += 1

# count number of #nofilter with filters
norm_filter_count = 0
some_filter_count = 0
false_nofilter_count = 0
true_nofilter_count = 0

for p in media:
    # check if there is actually no filter
    if p.filter != 'Normal':
        some_filter_count += 1
        # check if there is a #nofilter hashtag     
        if 'tags' in p.__dict__.keys():
            if 'nofilter' in [t.name.lower() for t in p.tags]:
                false_nofilter_count += 1
    else:
        norm_filter_count += 1
        # check if there is a #nofilter hashtag     
        if 'tags' in p.__dict__.keys():
            if 'nofilter' in [t.name.lower() for t in p.tags]:
                true_nofilter_count += 1


################




################
# biggest fans
################
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
