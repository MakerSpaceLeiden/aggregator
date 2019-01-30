import time


class Aggregator(object):
    def __init__(self, mysql_adapter, redis_adapter, notifications_queue):
        self.mysql_adapter = mysql_adapter
        self.redis_adapter = redis_adapter
        self.notifications_queue = notifications_queue

    def _get_user_by_id(self, user_id, logger):
        user = self.redis_adapter.get_user_by_id(user_id, logger)
        if not user:
            all_users = self.mysql_adapter.get_all_users(logger)
            self.redis_adapter.set_users_by_ids(all_users, logger)
            filtered_users = [u for u in all_users if u.user_id == user_id]
            if len(filtered_users) == 1:
                user = filtered_users[0]
        return user

    def get_tags(self, logger):
        return self.mysql_adapter.get_all_tags(logger)

    def user_entered_space_door(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        if not user:
            raise Exception(f'User ID {user_id} not found in database')
        logger.info(f'user_entered_space_door: {user.full_name}')
        self.redis_adapter.store_user_in_space(user, time.time(), logger)
        self.notifications_queue.send_message(msg_type='user_entered_space')

    def get_space_state(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user_ids = self.redis_adapter.get_user_ids_in_space(logger)
        users = [self._get_user_by_id(user_id, logger) for user_id in user_ids]
        return [u for u in users if u]
