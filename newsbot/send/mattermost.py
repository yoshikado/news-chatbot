import json
from httplib2 import Http
from sqlite_util import SQLiteUtil

MM_WEBHOOK_USERNAME = "ミスター・ポポv2.0"
MM_ICON_URL = "https://www.mattermost.org/wp-content/uploads/2016/04/icon.png"


class Mattermost():
    def __init__(self, room_url):
        self.room_url = room_url
        self.username = MM_WEBHOOK_USERNAME
        self.icon_url = MM_ICON_URL

    def send(self, title, filtered_data):
        self.send_title(title)
        self.send_all_articles(filtered_data)

    def send_title(self, title):
        body = {
            "username": self.username,
            "icon_url": self.icon_url,
            "text": title
        }
        res = self.__send(body)

    def send_source_header(self, source):
        if len(source[1]['articles']):
            header = source[1]['name']
            imgurl = source[1]['img']
            body = {
                "username": self.username,
                "icon_url": self.icon_url,
                "attachments": [
                    {
                        "color": "#FF8000",
                        "title": header,
                    }
                ]
            }
            self.__send(body)

    def send_source_articles(self, source):
        sql = SQLiteUtil(source[0])
        for article in source[1]['articles']:
            text = "\n{}\n{}".format(article['link'],article['title'])
            body = {
                "username": self.username,
                "icon_url": self.icon_url,
                "text": text
            }
            self.__send(body)
            sql.UpdateSentData('true', article['title'])

    def send_all_articles(self, filtered_data):
        for source in filtered_data['newspapers'].items():
            # Create card with the source title
            self.send_source_header(source)
            # Send each articles
            self.send_source_articles(source)

    def __send(self, body):
        bot_message = body
        message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
        http_obj = Http()
        resp, content = http_obj.request(
            uri=self.room_url,
            method='POST',
            headers=message_headers,
            body=json.dumps(bot_message),
        )
        print("uri={}, headers={}, body={}".format(self.room_url, message_headers, body))
        print("response: {}".format(resp))
        print("content: {}".format(content))
        return content.decode('utf-8')
