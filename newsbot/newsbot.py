import click
import feedparser as fp
import json
import newspaper
from copy import deepcopy
from newspaper import Article
from sqlite_util import SQLiteUtil
from httplib2 import Http

DEFAULT_NEWS_LIST_FILE = "news_list.json"

keywordList = [
    'Canonical',
    'カノニカル',
    'ubuntu',
    'linux',
    'openstack',
    'kubernetes',
    'redhat',
    'Red hat',
    'レッドハット',
    'Microsoft',
    'マイクロソフト',
    'Yahoo!Japan',
    'ヤフー',
    '買収',
    '日立製作所',
    'VMware',
    'IBM',
    'SUSE',
    'Dell',
    'Intel',
    'インテル',
    'Mellanox',
    'メラノックス',
    'Sony',
    'ソニー',
    'nuc',
    'ThinkPad',
]

gChatRoomUrl = None
gThreadSpace = None


def aggregateAllNews(file):
    data = {}
    data['newspapers'] = {}
    # Load the news_list.json
    with open(file) as data_file:
        sources = json.load(data_file)
    # Iterate through each news source
    rss_link = 'none'
    for source, value in sources.items():
        if 'rss' in value:
            rss_link = value['rss']
        homepage = value['link']
        newsPaper = aggregateNews(source, rss_link, homepage)
        data['newspapers'][source] = newsPaper
    return data


def aggregateNews(name, rss_link, homepage):
    pageContent = Article(homepage)
    pageContent.download()
    pageContent.parse()
    newsPaper = {
        "name": pageContent.title,
        "rss": rss_link,
        "homepage": homepage,
        "img": pageContent.meta_img,
        "articles": []
    }
    sql = SQLiteUtil(name)
    if rss_link != 'none':
        print("Downloading articles from ", name)
        d = fp.parse(rss_link)
        newsPaper.update(name=d.feed.title)
        for entry in d.entries:
            try:
                content = Article(entry.link)
                content.download()
                content.parse()
            except Exception as e:
                # If the download for some reason fails (ex. 404)
                # the script will continue downloading the next article.
                print(e)
                print("continuing...")
                continue
            article = {}
            article['title'] = entry.title
            article['link'] = entry.link
            article['published'] = None
            article['authors'] = None
            article['summary'] = None
            article['sent'] = 'false'
            if hasattr(entry, 'published'):
                article['published'] = entry.published
            elif content.publish_date:
                article['published'] = content.publish_date.isoformat()
            if hasattr(entry, 'author'):
                article['authors'] = entry.author
            if hasattr(entry, 'summary'):
                article['summary'] = entry.summary
            newsPaper['articles'].append(article)
            sql.WriteArticleToDB(article)
            print('articles downloaded from {},'
                  'url: {}'.format(name, entry.link))
    else:
        # This is the fallback method if a RSS-feed link is not provided.
        # It uses the python newspaper library to extract articles
        print("Building site for ", name)
        paper = newspaper.build(homepage, memoize_articles=False)
        for content in paper.articles:
            try:
                content.download()
                content.parse()
            except Exception as e:
                print(e)
                print("continuing...")
                continue
            # Again, for consistency, if there is no found publish date
            # the article will be skipped.
            article = {}
            article['title'] = content.title
            article['link'] = content.url
            article['published'] = content.publish_date
            article['authors'] = None
            article['summary'] = None
            article['sent'] = 'false'
            if content.authors:
                article['authors'] = content.authors
            if content.summary:
                article['summary'] = content.summary
            newsPaper['articles'].append(article)
            sql.WriteArticleToDB(article)
            print('articles downloaded from {} \
                   using newspaper, url: {}'.format(name, content.url))
    return newsPaper


def filterNews(data):
    filtered_data = deepcopy(data)
    for source in data['newspapers'].items():
        filterWithKeywords(source, filtered_data['newspapers'][source[0]])
        sql = SQLiteUtil(source[0])
        if not filtered_data['newspapers'][source[0]]['articles']:
            filterDuplicates(sql,
                            filtered_data['newspapers'][source[0]]['articles'])
    return filtered_data


def filterWithKeywords(source, filtered_data):
    for article in source[1]['articles']:
        keyFound = False
        for keyword in keywordList:
            if keyword in article['title']:
                keyFound = True
                break
        if not keyFound:
            filtered_data['articles'].remove(article)


def filterDuplicates(sql, filtered_articles):
    articles = deepcopy(filtered_articles)
    column = 'sent'
    for article in articles:
        dp = sql.SelectColumnFromTitle(column, article['title'])
        if "true" in dp:
            filtered_articles.remove(article)


def getThreadSpace(res):
    r = json.loads(res)
    return r['thread']['name']


def sendSourceHeader(source):
    global gThreadSpace
    if len(source[1]['articles']):
        header = source[1]['name']
        imgurl = source[1]['img']
        body = {
            "cards": [
                {
                    "header": {
                        "title": header,
                        "imageUrl": imgurl
                    }
                }
            ],
            "thread": {
                "name": gThreadSpace
            }
        }
        send(body)


def sendSourceArticles(source):
    global gThreadSpace
    sql = SQLiteUtil(source[0])
    for article in source[1]['articles']:
        text = "\n{}\n{}".format(article['title'], article['link'])
        body = {
            "text": text,
            "thread": {
                "name": gThreadSpace
            }
        }
        send(body)
        sql.UpdateSentData('true', article['title'])


def sendAllArticles(filtered_data):
    for source in filtered_data['newspapers'].items():
        # Create card with the source title
        sendSourceHeader(source)
        # Send each articles
        sendSourceArticles(source)


def sendTitle(title):
    global gThreadSpace
    body = {'text': title}
    res = send(body)
    gThreadSpace = getThreadSpace(res)


def send(body):
    global gChatRoomUrl
    bot_message = body
    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
    http_obj = Http()
    resp, content = http_obj.request(
        uri=gChatRoomUrl,
        method='POST',
        headers=message_headers,
        body=json.dumps(bot_message),
    )
    print(resp)
    return content.decode('utf-8')


def sendToChat(filtered_data, title):
    sendTitle(title)
    sendAllArticles(filtered_data)


@click.command()
@click.option('--room', required=True,
              help='Specify the Room URL to send.')
@click.option('-f', '--file', default=DEFAULT_NEWS_LIST_FILE,
              help='specify a file with news list(JSON format). \
              default=news_list.json')
@click.option('-t', '--title', default="Today's news digest!",
              help='Set the title. default="Today\'s news digest!"')
def main(room, file, title):
    global gChatRoomUrl
    gChatRoomUrl = room
    data = aggregateAllNews(file)
    filtered_data = filterNews(data)
    sendToChat(filtered_data, title)


if __name__ == '__main__':
    main()
