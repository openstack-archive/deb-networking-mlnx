# Copyright 2015 Mellanox Technologies, Ltd
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
import datetime

import mock
import requests

from neutron.db import api as neutron_db_api
from neutron.plugins.common import constants
from neutron.plugins.ml2 import config
from neutron.plugins.ml2 import plugin
from neutron.tests.unit.plugins.ml2 import test_plugin
from neutron.tests.unit import testlib_api
from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from networking_mlnx.db import db
from networking_mlnx.journal import cleanup
from networking_mlnx.journal import journal
from networking_mlnx.plugins.ml2.drivers.sdn import client
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const
from networking_mlnx.plugins.ml2.drivers.sdn import sdn_mech_driver
from networking_mlnx.plugins.ml2.drivers.sdn import utils as sdn_utils

PLUGIN_NAME = 'neutron.plugins.ml2.plugin.Ml2Plugin'
SEG_ID = 4
DEVICE_OWNER_COMPUTE = 'compute:None'
MECHANISM_DRIVER_NAME = 'mlnx_sdn_assist'


class SdnConfigBase(test_plugin.Ml2PluginV2TestCase):

    def setUp(self):
        super(SdnConfigBase, self).setUp()
        config.cfg.CONF.set_override('mechanism_drivers',
                                     ['logger', MECHANISM_DRIVER_NAME],
                                     'ml2')
        config.cfg.CONF.set_override('url', 'http://127.0.0.1/neo',
                                     sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('username', 'admin', sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('password', 'admin', sdn_const.GROUP_OPT)


class SdnTestCase(SdnConfigBase):

    def setUp(self):
        super(SdnTestCase, self).setUp()
        self.mech = sdn_mech_driver.SDNMechanismDriver()
        mock.patch.object(journal.SdnJournalThread,
                          'start_sync_thread').start()
        self.mock_request = mock.patch.object(client.SdnRestClient,
                                              'request').start()
        self.mock_request.side_effect = self.check_request

    def check_request(self, method, urlpath, obj):
        self.assertFalse(urlpath.startswith("http://"))


class SdnMechanismConfigTests(testlib_api.SqlTestCase):

    def _set_config(self, url='http://127.0.0.1/neo',
                    username='admin',
                    password='admin'):
        config.cfg.CONF.set_override('mechanism_drivers',
                                     ['logger', MECHANISM_DRIVER_NAME],
                                     'ml2')
        config.cfg.CONF.set_override('url', url, sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('username', username, sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('password', password, sdn_const.GROUP_OPT)

    def _test_missing_config(self, **kwargs):
        self._set_config(**kwargs)
        self.assertRaises(config.cfg.RequiredOptError,
                          plugin.Ml2Plugin)

    def test_valid_config(self):
        self._set_config()
        plugin.Ml2Plugin()

    def test_missing_url_raises_exception(self):
        self._test_missing_config(url=None)

    def test_missing_username_raises_exception(self):
        self._test_missing_config(username=None)

    def test_missing_password_raises_exception(self):
        self._test_missing_config(password=None)

    class SdnMechanismTestBasicGet(test_plugin.TestMl2BasicGet,
                                   SdnTestCase):
        pass

    class SdnMechanismTestNetworksV2(test_plugin.TestMl2NetworksV2,
                                     SdnTestCase):
        pass

    class SdnMechanismTestPortsV2(test_plugin.TestMl2PortsV2,
                                  SdnTestCase):
        pass


class DataMatcher(object):

    def __init__(self, context, object_type):
        self._data = context.__dict__["_" + object_type.lower()]

    def __eq__(self, data):
        return jsonutils.loads(data) == self._data

    def __repr__(self):
        return jsonutils.dumps(self._data)


class SdnDriverTestCase(SdnConfigBase):

    OPERATION_MAPPING = {
        sdn_const.PUT: 'update',
        sdn_const.DELETE: 'delete',
        sdn_const.POST: 'create',
    }

    def setUp(self):
        super(SdnDriverTestCase, self).setUp()
        self.db_session = neutron_db_api.get_session()
        self.mech = sdn_mech_driver.SDNMechanismDriver()
        self.mock_sync_thread = mock.patch.object(
            journal.SdnJournalThread, 'start_sync_thread').start()
        self.mech.initialize()
        self.thread = journal.SdnJournalThread()
        self.addCleanup(self._db_cleanup)

    def _get_segments_list(self, seg_id=SEG_ID, net_type=constants.TYPE_VLAN):
        return [{'segmentation_id': seg_id,
                'physical_network': u'physnet1',
                'id': u'c13bba05-eb07-45ba-ace2-765706b2d701',
                'network_type': net_type}]

    def _get_mock_network_operation_context(self):
        current = {"provider:segmentation_id": SEG_ID,
                   'id': 'c13bba05-eb07-45ba-ace2-765706b2d701',
                   'name': 'net1',
                   'provider:network_type': 'vlan',
                   'network_qos_policy': None}
        context = mock.Mock(current=current, _network=current,
                            _segments=self._get_segments_list())
        context._plugin_context.session = neutron_db_api.get_session()
        return context

    def _get_mock_port_operation_context(self):
        current = {'binding:host_id': 'r-ufm177',
                   'binding:profile': {u'pci_slot': u'0000:02:00.4',
                                       u'physical_network': u'physnet1',
                                       u'pci_vendor_info': u'15b3:1004'},
                   'id': '72c56c48-e9b8-4dcf-b3a7-0813bb3bd839',
                   'binding:vnic_type': 'direct',
                   'mac_address': '12:34:56:78:21:b6',
                   'name': 'port_test1',
                   'network_id': 'c13bba05-eb07-45ba-ace2-765706b2d701',
                   'network_qos_policy': None}
        original = {'binding:host_id': None,
                    'binding:profile': {u'pci_slot': None,
                                        u'physical_network': u'physnet1',
                                        u'pci_vendor_info': u'15b3:1004'},
                    'id': None,
                    'binding:vnic_type': None,
                    'mac_address': None,
                    'name': None,
                    'network_id': 'c13bba05-eb07-45ba-ace2-765706b2d701',
                    'network_qos_policy': None}

        # The port context should have NetwrokContext object that contain
        # the segments list
        network_context = type('NetworkContext', (object,),
                            {"_segments": self._get_segments_list()})

        context = mock.Mock(current=current, _port=current,
                            original=original,
                            _network_context=network_context)
        context._plugin_context.session = neutron_db_api.get_session()
        return context

    def _get_mock_bind_operation_context(self):
        current = {'binding:host_id': 'r-ufm177',
                   'binding:profile': {u'pci_slot': u'0000:02:00.4',
                                       u'physical_network': u'physnet1',
                                       u'pci_vendor_info': u'15b3:1004'},
                   'id': '72c56c48-e9b8-4dcf-b3a7-0813bb3bd839',
                   'binding:vnic_type': 'direct',
                   'mac_address': '12:34:56:78:21:b6',
                   'name': 'port_test1',
                   'device_owner': DEVICE_OWNER_COMPUTE,
                   'network_id': 'c13bba05-eb07-45ba-ace2-765706b2d701',
                   'network_qos_policy': None}
        context = mock.Mock(current=current, _port=current,
                            segments_to_bind=self._get_segments_list())
        context._plugin_context.session = neutron_db_api.get_session()
        return context

    def _get_mock_operation_context(self, object_type):
        getter = getattr(self, '_get_mock_%s_operation_context' %
                         object_type.lower())
        return getter()

    _status_code_msgs = {
        200: '',
        201: '',
        204: '',
        400: '400 Client Error: Bad Request',
        401: '401 Client Error: Unauthorized',
        403: '403 Client Error: Forbidden',
        404: '404 Client Error: Not Found',
        409: '409 Client Error: Conflict',
        501: '501 Server Error: Not Implemented',
        503: '503 Server Error: Service Unavailable',
    }

    def _get_http_request_codes(self):
        for err_code in (requests.codes.ok,
                         requests.codes.created,
                         requests.codes.no_content,
                         requests.codes.bad_request,
                         requests.codes.unauthorized,
                         requests.codes.forbidden,
                         requests.codes.not_found,
                         requests.codes.conflict,
                         requests.codes.not_implemented,
                         requests.codes.service_unavailable):
            yield err_code

    def _db_cleanup(self):
        rows = db.get_all_db_rows(self.db_session)
        for row in rows:
            db.delete_row(self.db_session, row=row)

    @classmethod
    def _get_mock_request_response(cls, status_code, job_url):
        response = mock.Mock(status_code=status_code)
        if status_code < 400:
            response.raise_for_status = mock.Mock()
            response.json = mock.Mock(
                side_effect=[job_url, {"Status": "Completed"}])
        else:
            mock.Mock(side_effect=requests.exceptions.HTTPError(
                cls._status_code_msgs[status_code]))

        return response

    def _test_operation(self, method, status_code, expected_calls,
                        *args, **kwargs):
        job_url = 'app/jobs/' + uuidutils.generate_uuid()
        urlpath = sdn_utils.strings_to_url(
            cfg.CONF.sdn.url, job_url)

        request_response = self._get_mock_request_response(
            status_code, job_url)
        if expected_calls == 4 and status_code < 400:
            job_url2 = 'app/jobs/' + uuidutils.generate_uuid()
            urlpath2 = sdn_utils.strings_to_url(
                cfg.CONF.sdn.url, job_url)
            request_response.json = mock.Mock(
                side_effect=[job_url, job_url2,
                {"Status": "Completed"}, {"Status": "Completed"}])
        with mock.patch('requests.Session.request',
                        return_value=request_response) as mock_method:

            method(exit_after_run=True)
            login_args = mock.call(
                sdn_const.POST, mock.ANY,
                headers=sdn_const.LOGIN_HTTP_HEADER,
                data=mock.ANY, timeout=config.cfg.CONF.sdn.timeout)
            job_get_args = mock.call(
                sdn_const.GET, data=None,
                headers=sdn_const.JSON_HTTP_HEADER,
                url=urlpath, timeout=config.cfg.CONF.sdn.timeout)
            if status_code < 400:
                if expected_calls:
                    operation_args = mock.call(
                        headers=sdn_const.JSON_HTTP_HEADER,
                        timeout=config.cfg.CONF.sdn.timeout, *args, **kwargs)
                    if expected_calls == 4:
                        urlpath2 = sdn_utils.strings_to_url(
                            cfg.CONF.sdn.url, job_url2)
                        job_get_args2 = mock.call(
                            sdn_const.GET, data=None,
                            headers=sdn_const.JSON_HTTP_HEADER,
                            url=urlpath2, timeout=config.cfg.CONF.sdn.timeout)
                        self.assertEqual(
                            login_args, mock_method.mock_calls[4])
                        self.assertEqual(
                            job_get_args, mock_method.mock_calls[5])
                        self.assertEqual(
                            login_args, mock_method.mock_calls[6])
                        self.assertEqual(
                            job_get_args2, mock_method.mock_calls[7])
                    else:
                        self.assertEqual(
                            login_args, mock_method.mock_calls[0])
                        self.assertEqual(
                            operation_args, mock_method.mock_calls[1])
                        self.assertEqual(
                            login_args, mock_method.mock_calls[2])
                        self.assertEqual(
                            job_get_args, mock_method.mock_calls[3])

                # we need to reduce the login call_cout
                self.assertEqual(expected_calls * 2, mock_method.call_count)

    def _call_operation_object(self, operation, object_type):
        if object_type == sdn_const.PORT and operation == sdn_const.POST:
            context = self._get_mock_bind_operation_context()
            method = getattr(self.mech, 'bind_port')
        else:
            context = self._get_mock_operation_context(object_type)
            operation = self.OPERATION_MAPPING[operation]
            object_type = object_type.lower()
            method = getattr(self.mech, '%s_%s_precommit' % (operation,
                                                             object_type))
        method(context)

    def _test_operation_object(self, operation, object_type):
        self._call_operation_object(operation, object_type)

        context = self._get_mock_operation_context(object_type)
        row = db.get_oldest_pending_db_row_with_lock(self.db_session)
        self.assertEqual(operation, row['operation'])
        self.assertEqual(object_type, row['object_type'])
        self.assertEqual(context.current['id'], row['object_uuid'])

    def _test_thread_processing(self, operation, object_type,
                                expected_calls=2):
        status_codes = {sdn_const.POST: requests.codes.created,
                        sdn_const.PUT: requests.codes.ok,
                        sdn_const.DELETE: requests.codes.no_content}

        http_request = operation
        status_code = status_codes[operation]

        self._call_operation_object(operation, object_type)

        if object_type == sdn_const.PORT and operation == sdn_const.POST:
            context = self._get_mock_bind_operation_context()
        else:
            context = self._get_mock_operation_context(object_type)

        url_object_type = object_type.replace('_', '-')
        url = '%s/%s/%s' % (config.cfg.CONF.sdn.url,
                            config.cfg.CONF.sdn.domain,
                            url_object_type)
        if operation in (sdn_const.PUT, sdn_const.DELETE):
            uuid = context.current['id']
            url = '%s/%s' % (url, uuid)
        kwargs = {'url': url, 'data': DataMatcher(context, object_type)}
        with mock.patch.object(self.thread.event, 'wait',
                               return_value=False):
            self._test_operation(self.thread.run_sync_thread, status_code,
                                 expected_calls, http_request, **kwargs)

    def _test_object_type(self, object_type):
        # Add and process create request.
        self._test_thread_processing(sdn_const.POST, object_type)
        rows = db.get_all_db_rows_by_state(self.db_session,
                                           sdn_const.COMPLETED)
        self.assertEqual(1, len(rows))

        # Add and process update request. Adds to database.
        self._test_thread_processing(sdn_const.PUT, object_type)
        rows = db.get_all_db_rows_by_state(self.db_session,
                                           sdn_const.COMPLETED)
        self.assertEqual(2, len(rows))

        # Add and process update request. Adds to database.
        self._test_thread_processing(sdn_const.DELETE, object_type)
        rows = db.get_all_db_rows_by_state(self.db_session,
                                           sdn_const.COMPLETED)
        self.assertEqual(3, len(rows))

    def _test_object_type_pending_network(self, object_type):
        # Create a network (creates db row in pending state).
        self._call_operation_object(sdn_const.POST,
                                    sdn_const.NETWORK)

        # Create object_type database row and process. This results in both
        # the object_type and network rows being processed.
        self._test_thread_processing(sdn_const.POST, object_type,
                                     expected_calls=4)

        # Verify both rows are now marked as completed.
        rows = db.get_all_db_rows_by_state(self.db_session,
                                           sdn_const.COMPLETED)
        self.assertEqual(2, len(rows))

    def _test_object_type_processing_network(self, object_type):
        self._test_object_operation_pending_another_object_operation(
            object_type, sdn_const.POST, sdn_const.NETWORK,
            sdn_const.POST)

    def _test_object_operation_pending_object_operation(
        self, object_type, operation, pending_operation):
        self._test_object_operation_pending_another_object_operation(
            object_type, operation, object_type, pending_operation)

    def _test_object_operation_pending_another_object_operation(
        self, object_type, operation, pending_type, pending_operation):
        # Create the object_type (creates db row in pending state).
        self._call_operation_object(pending_operation,
                                    pending_type)

        # Get pending row and mark as processing so that
        # this row will not be processed by journal thread.
        row = db.get_all_db_rows_by_state(self.db_session, sdn_const.PENDING)
        db.update_db_row_state(self.db_session, row[0], sdn_const.PROCESSING)

        # Create the object_type database row and process.
        # Verify that object request is not processed because the
        # dependent object operation has not been marked as 'completed'.
        self._test_thread_processing(operation,
                                     object_type,
                                     expected_calls=0)

        # Verify that all rows are still in the database.
        rows = db.get_all_db_rows_by_state(self.db_session,
                                           sdn_const.PROCESSING)
        self.assertEqual(1, len(rows))
        rows = db.get_all_db_rows_by_state(self.db_session, sdn_const.PENDING)
        self.assertEqual(1, len(rows))

    def _test_parent_delete_pending_child_delete(self, parent, child):
        self._test_object_operation_pending_another_object_operation(
            parent, sdn_const.DELETE, child, sdn_const.DELETE)

    def _test_cleanup_processing_rows(self, last_retried, expected_state):
        # Create a dummy network (creates db row in pending state).
        self._call_operation_object(sdn_const.POST,
                                    sdn_const.NETWORK)

        # Get pending row and mark as processing and update
        # the last_retried time
        row = db.get_all_db_rows_by_state(self.db_session,
                                          sdn_const.PENDING)[0]
        row.last_retried = last_retried
        db.update_db_row_state(self.db_session, row, sdn_const.PROCESSING)

        # Test if the cleanup marks this in the desired state
        # based on the last_retried timestamp
        cleanup.JournalCleanup().cleanup_processing_rows(self.db_session)

        # Verify that the Db row is in the desired state
        rows = db.get_all_db_rows_by_state(self.db_session, expected_state)
        self.assertEqual(1, len(rows))

    def test_driver(self):
        for operation in (sdn_const.POST, sdn_const.PUT,
                          sdn_const.DELETE):
            for object_type in (sdn_const.NETWORK, sdn_const.PORT):
                self._test_operation_object(operation, object_type)

    def test_network(self):
        self._test_object_type(sdn_const.NETWORK)

    def test_network_update_pending_network_create(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.NETWORK, sdn_const.PUT, sdn_const.POST)

    def test_network_delete_pending_network_create(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.NETWORK, sdn_const.DELETE, sdn_const.POST)

    def test_network_delete_pending_network_update(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.NETWORK, sdn_const.DELETE, sdn_const.PUT)

    def test_network_delete_pending_port_delete(self):
        self._test_parent_delete_pending_child_delete(
            sdn_const.NETWORK, sdn_const.PORT)

    def test_port1(self):
        self._test_object_type(sdn_const.PORT)

    def test_port_update_pending_port_create(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.PORT, sdn_const.PUT, sdn_const.POST)

    def test_port_delete_pending_port_create(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.PORT, sdn_const.DELETE, sdn_const.POST)

    def test_port_delete_pending_port_update(self):
        self._test_object_operation_pending_object_operation(
            sdn_const.PORT, sdn_const.DELETE, sdn_const.PUT)

    def test_port_pending_network(self):
        self._test_object_type_pending_network(sdn_const.PORT)

    def test_port_processing_network(self):
        self._test_object_type_processing_network(sdn_const.PORT)

    def test_cleanup_processing_rows_time_not_expired(self):
        self._test_cleanup_processing_rows(datetime.datetime.utcnow(),
                                           sdn_const.PROCESSING)

    def test_cleanup_processing_rows_time_expired(self):
        old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        self._test_cleanup_processing_rows(old_time, sdn_const.PENDING)

    def test_thread_call(self):
        """Verify that the sync thread method is called."""

        # Create any object that would spin up the sync thread via the
        # decorator call_thread_on_end() used by all the event handlers.
        self._call_operation_object(sdn_const.POST,
                                    sdn_const.NETWORK)

        # Verify that the thread call was made.
        self.assertTrue(self.mock_sync_thread.called)

    def _decrease_row_created_time(self, row):
        row.created_at -= datetime.timedelta(hours=1)
        self.db_session.merge(row)
        self.db_session.flush()

    def test_sync_multiple_updates(self):
        # add 2 updates
        for i in range(2):
            self._call_operation_object(sdn_const.PUT,
                                        sdn_const.NETWORK)

        # get the last update row
        last_row = db.get_all_db_rows(self.db_session)[-1]

        # change the last update created time
        self._decrease_row_created_time(last_row)

        # create 1 more operation to trigger the sync thread
        # verify that there are no calls to NEO controller, because the
        # first row was not valid (exit_after_run = true)
        self._test_thread_processing(sdn_const.PUT,
                                     sdn_const.NETWORK, expected_calls=0)

        # validate that all the rows are in 'pending' state
        # first row should be set back to 'pending' because it was not valid
        rows = db.get_all_db_rows_by_state(self.db_session, sdn_const.PENDING)
        self.assertEqual(3, len(rows))
