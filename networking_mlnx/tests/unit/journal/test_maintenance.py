# Copyright 2016 Mellanox Technologies, Ltd
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import mock
import threading

from neutron.db import api as neutron_db_api
from neutron.tests.unit import testlib_api

from networking_mlnx.db.models import sdn_maintenance_db
from networking_mlnx.journal import maintenance
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const


class MaintenanceThreadTestCase(testlib_api.SqlTestCaseLight):
    def setUp(self):
        super(MaintenanceThreadTestCase, self).setUp()
        self.db_session = neutron_db_api.get_session()

        row = sdn_maintenance_db.SdnMaintenance(state=sdn_const.PENDING)
        self.db_session.add(row)
        self.db_session.flush()

        self.thread = maintenance.MaintenanceThread()
        self.thread.maintenance_interval = 0.01

    def test__execute_op_no_exception(self):
        with mock.patch.object(maintenance, 'LOG') as mock_log:
            operation = mock.MagicMock()
            operation.__name__ = "test"
            self.thread._execute_op(operation, self.db_session)
            self.assertTrue(operation.called)
            self.assertTrue(mock_log.info.called)
            self.assertFalse(mock_log.exception.called)

    def test__execute_op_with_exception(self):
        with mock.patch.object(maintenance, 'LOG') as mock_log:
            operation = mock.MagicMock(side_effect=Exception())
            operation.__name__ = "test"
            self.thread._execute_op(operation, self.db_session)
            self.assertTrue(mock_log.exception.called)

    def test_thread_works(self):
        callback_event = threading.Event()
        count = [0]

        def callback_op(**kwargs):
            count[0] += 1

            # The following should be true on the second call, so we're making
            # sure that the thread runs more than once.
            if count[0] > 1:
                callback_event.set()

        self.thread.register_operation(callback_op)
        self.thread.start()

        # Make sure the callback event was called and not timed out
        self.assertTrue(callback_event.wait(timeout=5))

    def test_thread_continues_after_exception(self):
        exception_event = threading.Event()
        callback_event = threading.Event()

        def exception_op(**kwargs):
            if not exception_event.is_set():
                exception_event.set()
                raise Exception()

        def callback_op(**kwargs):
            callback_event.set()

        for op in [exception_op, callback_op]:
            self.thread.register_operation(op)

        self.thread.start()

        # Make sure the callback event was called and not timed out
        self.assertTrue(callback_event.wait(timeout=5))
