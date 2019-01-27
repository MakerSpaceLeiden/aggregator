import mysql.connector
from aggregator.model import User


class MySQLAdapter(object):
    def __init__(self):
        self.db = mysql.connector.connect(
            host="localhost",
            db="makerspace"
        )

    def get_list_of_users(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all users')
        mycursor = self.db.cursor()
        mycursor.execute("SELECT id, first_name, last_name, email FROM members_user")
        return [User(*row) for row in mycursor]
