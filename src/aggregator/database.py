import mysql.connector
from contextlib import contextmanager
from aggregator.model import User, Tag, Machine


class MySQLAdapter(object):
    def __init__(self, host, database, port, user=None, password=None):
        self.host = host
        self.database = database
        self.port = port
        self.user = user
        self.password = password

    @contextmanager
    def _connection(self):
        db = mysql.connector.connect(host=self.host, database=self.database, port=self.port, user=self.user, password=self.password)
        yield db
        db.close()

    def get_all_users(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all users')
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute("SELECT id, first_name, last_name, email FROM members_user")
        return [User(*row) for row in mycursor]

    def get_all_machines(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all machines')
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute("SELECT id, name, description, node_machine_name, node_name FROM acl_machine WHERE node_machine_name IS NOT NULL AND node_machine_name <> ''")
        return [Machine(*row) for row in mycursor]

    def get_all_tags(self, logger):
        logger = logger.getLogger(subsystem='mysql')
        logger.info('Reading all tags')
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute('''
                SELECT members_tag.id AS tag_id, members_tag.tag, members_user.id AS user_id, first_name, last_name, email 
                FROM members_tag LEFT JOIN members_user ON (members_tag.owner_id = members_user.id)
            ''')
        return [Tag(row[0], row[1], User(*row[2:])) for row in mycursor]


class MockDatabaseAdapter(object):
    def __init__(self, all_users, all_machines):
        self.all_users = all_users
        self.all_machines = all_machines

    def get_all_users(self, logger):
        return self.all_users

    def get_all_machines(self, logger):
        return self.all_machines
