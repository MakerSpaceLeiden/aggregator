from contextlib import contextmanager

import mysql.connector

from aggregator.model import Machine, Tag, User


class MySQLAdapter(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @contextmanager
    def _connection(self):
        db = mysql.connector.connect(**self.__dict__)
        yield db
        db.close()

    def get_all_users(self, logger):
        logger = logger.getLogger(subsystem="mysql")
        logger.info("Reading all users")
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute(
                "SELECT id, first_name, last_name, email, telegram_user_id, phone_number, uses_signal, always_uses_email FROM members_user"
            )
        return [User(*row) for row in mycursor]

    def get_all_machines(self, logger):
        logger = logger.getLogger(subsystem="mysql")
        logger.info("Reading all machines")
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute(
                """
                SELECT acl_machine.id, acl_machine.name, acl_machine.description, node_machine_name, node_name, acl_location.name
                FROM acl_machine
                LEFT JOIN acl_location ON (acl_machine.location_id = acl_location.id)
                WHERE node_machine_name IS NOT NULL
                  AND node_machine_name <> ''
            """
            )
        return [Machine(*row) for row in mycursor]

    def get_all_tags(self, logger):
        logger = logger.getLogger(subsystem="mysql")
        logger.info("Reading all tags")
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute(
                """
                SELECT members_tag.id AS tag_id, members_tag.tag, members_user.id AS user_id, first_name, last_name, email
                FROM members_tag LEFT JOIN members_user ON (members_tag.owner_id = members_user.id)
            """
            )
        return [Tag(row[0], row[1], User(*row[2:])) for row in mycursor]

    def store_telegram_user_id_for_user_id(self, telegram_user_id, user_id, logger):
        logger = logger.getLogger(subsystem="mysql")
        logger.info(
            f"Registering user {user_id} with Telegram User ID {telegram_user_id}"
        )
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute(
                """
                UPDATE members_user SET telegram_user_id = %s WHERE id = %s
            """,
                (telegram_user_id, user_id),
            )
            db.commit()

    def delete_telegram_user_id_for_user_id(self, user_id, logger):
        logger = logger.getLogger(subsystem="mysql")
        logger.info(f"Clearing Telegram User ID for user {user_id}")
        with self._connection() as db:
            mycursor = db.cursor()
            mycursor.execute(
                """
                UPDATE members_user SET telegram_user_id = NULL WHERE id = %s
            """,
                (user_id,),
            )
            db.commit()
