from .testing_utils import AggregatorBaseTestSuite, STEFANO, BOB


class TestApplicationLogic(AggregatorBaseTestSuite):
    def test_enter_and_leave_space(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])
        self.assertEqual(space_state['history'], [])

        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [{
            'machines_on': [],
            'ts_checkin': '08:54:59 03/02/2019',
            'ts_checkin_human': 'a moment ago',
            'user': {'email': 'stefano@stefanomasini.com',
                     'first_name': 'Stefano',
                     'full_name': 'Stefano Masini',
                     'last_name': 'Masini',
                     'user_id': 1}}
        ])

        self.clock.add(1, 'hour')
        self.aggregator.user_left_space(STEFANO.user_id, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])
        self.assertEqual(space_state['history'], [{
            'description': 'User Stefano Masini entered the space at 08:54:59 03/02/2019',
            'first_name': 'Stefano',
            'hl_type': 'UserEntered',
            'last_name': 'Masini',
            'ts': 1549180499,
            'user_id': 1
        }, {
            'description': 'User Stefano Masini left the space at 09:54:59 03/02/2019',
            'first_name': 'Stefano',
            'hl_type': 'UserLeft',
            'last_name': 'Masini',
            'ts': 1549184099,
            'user_id': 1
        }])

    def test_chores(self):
        chores_state = self.aggregator.get_chores_for_json(self.logger)
        self.assertEqual(chores_state, {
            'events': [{'chore': {'chore_id': 1,
                                  'description': 'Empty trash every 2 weeks',
                                  'min_required_people': 2,
                                  'name': 'Empty trash'},
                        'when': {'human_str': '07:30:00 26/02/2019',
                                 'timestamp': 1551162600}},
                       {'chore': {'chore_id': 1,
                                  'description': 'Empty trash every 2 weeks',
                                  'min_required_people': 2,
                                  'name': 'Empty trash'},
                        'when': {'human_str': '07:30:00 12/03/2019',
                                 'timestamp': 1552372200}},
                       {'chore': {'chore_id': 1,
                                  'description': 'Empty trash every 2 weeks',
                                  'min_required_people': 2,
                                  'name': 'Empty trash'},
                        'when': {'human_str': '07:30:00 26/03/2019',
                                 'timestamp': 1553581800}},
                       {'chore': {'chore_id': 1,
                                  'description': 'Empty trash every 2 weeks',
                                  'min_required_people': 2,
                                  'name': 'Empty trash'},
                        'when': {'human_str': '08:30:00 09/04/2019',
                                 'timestamp': 1554791400}},
                       {'chore': {'chore_id': 1,
                                  'description': 'Empty trash every 2 weeks',
                                  'min_required_people': 2,
                                  'name': 'Empty trash'},
                        'when': {'human_str': '08:30:00 23/04/2019',
                                 'timestamp': 1556001000}}]

        })

    def test_stale_checkout_detection(self):
        # Check in at 11pm
        self.clock.set_time_of_day('23:00')
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        # After an hour (at midnight)
        self.clock.add(1, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [
            {
                'ts_checkin': '23:00:00 03/02/2019',
                'ts_checkin_human': 'an hour ago',
                'user': {
                    'email': 'stefano@stefanomasini.com',
                    'first_name': 'Stefano',
                    'full_name': 'Stefano Masini',
                    'last_name': 'Masini',
                    'user_id': 1,
                },
                'machines_on': [],
            },
        ])

        # At 5 am
        self.clock.add(5, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [
            {
                'ts_checkin': '23:00:00 03/02/2019',
                'ts_checkin_human': '6 hours ago',
                'user': {
                    'email': 'stefano@stefanomasini.com',
                    'first_name': 'Stefano',
                    'full_name': 'Stefano Masini',
                    'last_name': 'Masini',
                    'user_id': 1,
                },
                'machines_on': [],
            },
        ])

        # Detect stale checkins
        self.aggregator.clean_stale_user_checkins(self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])
        self.assertEqual(self.bot_messages, [])

        # At 9 am
        self.clock.add(4, 'hour')
        self.task_scheduler.actually_execute_due_tasks(self.logger)
        self.assertEqual(self.bot_messages, [
            (1, 'StaleCheckoutNotification'),
        ])
        self.bot_messages = []
        self.assertEqual(self.emails_sent, [
            (1, 'StaleCheckoutNotification'),
        ])

        # No more messages after that
        self.task_scheduler.actually_execute_due_tasks(self.logger)
        self.assertEqual(self.bot_messages, [])

    def test_warn_user_when_he_leaves_and_his_machine_is_on(self):
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        self.aggregator.user_activated_machine(STEFANO.user_id, 'tablesaw', self.logger)
        self.aggregator.machine_power('tablesaw', 'on', self.logger)

        self.aggregator.user_left_space(STEFANO.user_id, self.logger)

        self.assertEqual(self.bot_messages, [(1, 'ProblemsLeavingSpaceNotification')])
        problems = [p.__class__.__name__ for p in self.bot_notification_objects[0].problems]
        self.assertEqual(problems, ['ProblemMachineLeftOnByUser'])

    def test_warn_user_when_he_leaves_and_another_machine_is_on(self):
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        self.aggregator.user_activated_machine(BOB.user_id, 'tablesaw', self.logger)
        self.aggregator.machine_power('tablesaw', 'on', self.logger)

        # BOB left without checking out

        self.aggregator.user_left_space(STEFANO.user_id, self.logger)

        self.assertEqual(self.bot_messages, [(1, 'ProblemsLeavingSpaceNotification')])
        problems = [p.__class__.__name__ for p in self.bot_notification_objects[0].problems]
        self.assertEqual(problems, ['ProblemMachineLeftOnBySomeoneElse'])

    def test_warn_user_when_he_leaves_lights_on(self):
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)
        self.aggregator.lights('large_room', True, self.logger)

        self.aggregator.user_entered_space(BOB.user_id, self.logger)
        self.aggregator.user_left_space(BOB.user_id, self.logger)

        # No warning when BOB leaves because Stefano is still inside
        self.assertEqual(self.bot_messages, [])

        self.aggregator.user_left_space(STEFANO.user_id, self.logger)

        self.assertEqual(self.bot_messages, [(1, 'ProblemsLeavingSpaceNotification')])
        problems = [p.__class__.__name__ for p in self.bot_notification_objects[0].problems]
        self.assertEqual(problems, ['ProblemLightLeftOn'])

    def test_machine_on_and_off(self):
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [])
        self.assertEqual(space_state['users_in_space'], [
            {
                'machines_on': [],
                'ts_checkin': '08:54:59 03/02/2019',
                'ts_checkin_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1}
            }]
        )

        self.aggregator.user_activated_machine(STEFANO.user_id, 'tablesaw', self.logger)
        self.aggregator.machine_power('tablesaw', 'on', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [
            {
                'machine': {'name': 'Tablesaw', 'machine_id': 1}, 'ts': '08:54:59 03/02/2019', 'ts_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1},
                }
        ])
        self.assertEqual(space_state['users_in_space'], [
            {'machines_on': [{'machine': {'name': 'Tablesaw', 'machine_id': 1}, 'ts': '08:54:59 03/02/2019', 'ts_human': 'a moment ago',
                                                 'user': {'email': 'stefano@stefanomasini.com',
                                                          'first_name': 'Stefano',
                                                          'full_name': 'Stefano Masini',
                                                          'last_name': 'Masini',
                                                          'user_id': 1},
                                                 }],
                                'ts_checkin': '08:54:59 03/02/2019',
                                'ts_checkin_human': 'a moment ago',
                                'user': {'email': 'stefano@stefanomasini.com',
                                         'first_name': 'Stefano',
                                         'full_name': 'Stefano Masini',
                                         'last_name': 'Masini',
                                         'user_id': 1}
             }
        ])

        self.aggregator.machine_power('tablesaw', 'off', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [])
        self.assertEqual(space_state['users_in_space'], [
            {
                'machines_on': [],
                'ts_checkin': '08:54:59 03/02/2019',
                'ts_checkin_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1}}
        ])

    def test_space_open_and_closed(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], False)

        self.aggregator.space_open(True, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], True)

        self.aggregator.space_open(False, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], False)

    def test_lights_on_and_off(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [])

        self.aggregator.lights('large_room', True, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [{
            'label': 'large_room',
            'name': 'Large room',
        }])

        self.aggregator.lights('large_room', False, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [])
