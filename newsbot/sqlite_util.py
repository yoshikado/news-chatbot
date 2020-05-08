import sqlite3
from os import makedirs
from sqlite3 import Error


DB_DIR = './db'


class SQLiteUtil:
    """SQLite Util Class"""

    def __init__(self, db_name):
        self.conn = self.ConnectSQL(db_name)

    def __del__(self):
        try:
            self.conn.commit()
            self.conn.close()
            print("Connection closed with SQLite")
        except Error:
            print(Error)

    def ConnectSQL(self, db_name):
        """ create a database connection to the SQLite database
            specified by db_name
        :param db_name: database file
        :return: Connection object or None
        """
        conn = None
        makedirs(DB_DIR, exist_ok=True)
        db_file_path = '{}/{}.db'.format(DB_DIR, db_name)
        try:
            conn = sqlite3.connect(db_file_path)
            print("Connection established with SQLite")
            return conn
        except Error as e:
            print(e)

        return conn

    def CreateTable(self, create_table_sql):
        """ create a table from the create_table_sql statement
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        try:
            cur = self.conn.cursor()
            cur.execute(create_table_sql)
        except Error as e:
            print(e)

    def InsertArticle(self, article):
        """
        Insert a new article into the articles table
        :param article:
        """
        sql = ''' INSERT INTO articles(
                    title,
                    link,
                    authors,
                    published,
                    summary,
                    sent
                  )
                  VALUES(?,?,?,?,?,?) '''
        try:
            cur = self.conn.cursor()
            cur.execute(sql, article)
        except Error as e:
            print(e)

    def WriteArticleToDB(self, article):
        sql_articles_table = """ CREATE TABLE IF NOT EXISTS articles (
                                    title text NOT NULL UNIQUE,
                                    link text NOT NULL,
                                    authors text,
                                    published text,
                                    summary text,
                                    sent text NOT NULL
                                 ); """
        self.CreateTable(sql_articles_table)
        values = (
                    article['title'],
                    article['link'],
                    article['authors'],
                    article['published'],
                    article['summary'],
                    article['sent']
                )
        self.InsertArticle(values)

    def SelectColumnFromTitle(self, column, title):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT %s FROM articles WHERE title=?" % (column), (title,)
            )
        except Error as e:
            print(e)
        return cur.fetchone()

    def UpdateSentData(self, value, title):
        """
        update 'sent' in articles table
        :param value:
        :param title:
        """
        sql = ''' UPDATE articles
                SET sent = ?
                WHERE title = ?'''
        values = (
            value,
            title
        )
        try:
            cur = self.conn.cursor()
            cur.execute(sql, values)
        except Error as e:
            print(e)
