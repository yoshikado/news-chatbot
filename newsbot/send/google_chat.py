import json
from httplib2 import Http
from sqlite_util import SQLiteUtil


class GoogleChat():
    def __init__(self, room_url):
        self.room_url = room_url
        self.threadspace = None

    def send(self, title, filtered_data):
        self.send_title(title)
        self.send_all_articles(filtered_data)

    def set_thread_space(self, res):
        r = json.loads(res)
        self.threadspace = r['thread']['name']

    def send_source_header(self, source):
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
                    "name": self.threadspace
                }
            }
            self.__send(body)

    def send_source_articles(self, source):
        sql = SQLiteUtil(source[0])
        for article in source[1]['articles']:
            text = "\n{}\n{}".format(article['title'], article['link'])
            body = {
                "text": text,
                "thread": {
                    "name": self.threadspace
                }
            }
            self.__send(body)
            sql.UpdateSentData('true', article['title'])

    def send_all_articles(self, filtered_data):
        for source in filtered_data['newspapers'].items():
            # Create card with the source title
            self.send_source_header(source)
            # Send each articles
            self.send_source_articles(source)

    def send_title(self, title):
        body = {'text': title}
        res = self.__send(body)
        self.set_thread_space(res)

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
