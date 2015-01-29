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

print "Last picture posted at " + str(media[0].created_time)


media.reverse() # returned in recent order

likes = [p.like_count for p in media]
times = [p.created_time for p in media]
filters = [p.filter for p in media]
types = [p.type for p in media]

pic1 = recent_media[0]

# caption
print(pic1.caption.text)

# did i like it?
print(pic1.user_has_liked)

# how many likes
print(pic1.like_count)

# which users liked it...this only returns 4 for some reason
print(pic1.likes)

# filter
print(pic1.filter)

# comment count
print(pic1.comment_count)

# comments
print(pic1.comments)

for media in recent_media:
   print media.caption.text


