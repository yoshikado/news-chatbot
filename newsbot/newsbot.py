import click
import feedparser as fp
import json
import newspaper
from send.google_chat import GoogleChat
from send.mattermost import Mattermost
from copy import deepcopy
from newspaper import Article
from sqlite_util import SQLiteUtil

DEFAULT_NEWS_LIST_FILE = "news_list.json"

TOOL_GOOGLE_CHAT = 'google_chat'
TOOL_MATTERMOST = 'mattermost'

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
        if filtered_data['newspapers'][source[0]]['articles']:
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


def send(chat, filtered_data, title, room):
    if chat == TOOL_GOOGLE_CHAT:
        send = GoogleChat(room)
    elif chat == TOOL_MATTERMOST:
        send = Mattermost(room)
    send.send(title, filtered_data)


@click.command()
@click.option('--room', required=True,
              help='Specify the Room URL to send.')
@click.option('-f', '--file', default=DEFAULT_NEWS_LIST_FILE,
              help='specify a file with news list(JSON format). \
              default=news_list.json')
@click.option('-t', '--title', default="Today's news digest!",
              help='Set the title. default="Today\'s news digest!"')
@click.option('-c', '--chat', required=True,
              help='Which chat tool to send to. \
              google_chat, mattermost is supported')
def main(room, file, title, chat):
    data = aggregateAllNews(file)
    filtered_data = filterNews(data)
    send(chat, filtered_data, title, room)


if __name__ == '__main__':
    main()
