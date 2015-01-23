from instagram.client import InstagramAPI

with open('my_token.data', 'r') as f:
    acc_token = f.read()

api = InstagramAPI(access_token=acc_token)
recent_media, next_ = api.user_recent_media()

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


