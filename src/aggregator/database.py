import mysql.connector
from aggregator.model import User, Tag


class MySQLAdapter(object):
    def __init__(self, host, database, port, user=None, password=None):
        self.db = mysql.connector.connect(host=host, database=database, port=port, user=user, password=password)

    def get_all_users(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all users')
        mycursor = self.db.cursor()
        mycursor.execute("SELECT id, first_name, last_name, email FROM members_user")
        return [User(*row) for row in mycursor]

    def get_all_tags(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all tags')
        mycursor = self.db.cursor()
        mycursor.execute('''
            SELECT members_tag.id AS tag_id, members_tag.tag, members_user.id AS user_id, first_name, last_name, email 
            FROM members_tag LEFT JOIN members_user ON (members_tag.owner_id = members_user.id)
        ''')
        return [Tag(row[0], row[1], User(*row[2:])) for row in mycursor]


class MockDatabaseAdapter(object):
    def __init__(self, all_users):
        self.all_users = all_users

    def get_all_users(self, logger):
        return self.all_users
