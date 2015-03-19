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

import mock
from oslo_serialization import jsonutils
import requests

from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const
from networking_mlnx.plugins.ml2.drivers.sdn import sdn_mech_driver
from neutron.common import constants as neutron_const
from neutron.plugins.common import constants
from neutron.plugins.ml2 import config as config
from neutron.plugins.ml2 import driver_api as api

from neutron.plugins.ml2 import plugin
from neutron.tests import base
from neutron.tests.unit.plugins.ml2 import test_plugin
from neutron.tests.unit import testlib_api


PLUGIN_NAME = 'neutron.plugins.ml2.plugin.Ml2Plugin'
SEG_ID = 4L
DEVICE_OWNER_COMPUTE = "compute:None"


class SDNTestCase(test_plugin.Ml2PluginV2TestCase):
    _mechanism_drivers = ['logger', sdn_const.GROUP_OPT]

    def setUp(self):
        config.cfg.CONF.set_override('url', 'http://127.0.0.1:5001/cloudx_api',
                                     sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('username', 'admin', sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('password', 'admin', sdn_const.GROUP_OPT)

        super(SDNTestCase, self).setUp()
        self.mech = sdn_mech_driver.SDNMechanismDriver()
        sdn_mech_driver.SDNMechanismDriver._send_http_request = (
            self.check_send_http_request)

    def check_send_http_request(self, urlpath, data, method):
        self.assertFalse(urlpath.startswith("http://"))


class SDNMechanismConfigTests(testlib_api.SqlTestCase):

    def _set_config(self, url='http://127.0.0.1:5001/cloudx_api',
                    username='admin',
                    password='admin'):
        config.cfg.CONF.set_override('mechanism_drivers',
                                     ['logger', sdn_const.GROUP_OPT],
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


class AuthMatcher(object):

    def __eq__(self, obj):
        return (obj.username == config.cfg.CONF.sdn.username and
                obj.password == config.cfg.CONF.sdn.password)


class DataMatcher(object):

    def __init__(self, context, object_type):
        self._data = context.__dict__["_" + object_type.lower()]
        self._data = jsonutils.dumps(self._data, indent=2)

    def __eq__(self, data):
        return data == self._data


class SDNDriverTestCase(base.BaseTestCase):

    def setUp(self):
        super(SDNDriverTestCase, self).setUp()
        config.cfg.CONF.set_override('mechanism_drivers',
                                     ['logger', sdn_const.GROUP_OPT], 'ml2')
        config.cfg.CONF.set_override('url', 'http://127.0.0.1:5001/cloudx_api',
                                     sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('username', 'admin', sdn_const.GROUP_OPT)
        config.cfg.CONF.set_override('password', 'admin', sdn_const.GROUP_OPT)
        self.mech = sdn_mech_driver.SDNMechanismDriver()
        self.mech.initialize()

    def _get_segments_list(self, seg_id=SEG_ID, net_type=constants.TYPE_VLAN):
        return [{'segmentation_id': seg_id,
                'physical_network': u'physnet1',
                'id': u'72770a8a-e9b4-46da-8f0a-ffbd6a7fa3de',
                'network_type': net_type}]

    def _get_mock_network_operation_context(self):
        current = {"provider:segmentation_id": SEG_ID,
                   'id': 'd897e21a-dfd6-4331-a5dd-7524fa421c3e',
                   'name': 'net1',
                   'provider:network_type': 'vlan'}
        context = mock.Mock(current=current, _network=current,
                            _segments=self._get_segments_list())
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
                   'network_id': 'c13bba05-eb07-45ba-ace2-765706b2d701'}

        # The port context should have NetwrokContext object that contain
        # the segments list
        network_context = type('NetworkContext', (object,),
                            {"_segments": self._get_segments_list()})

        context = mock.Mock(current=current, _port=current,
                            _network_context=network_context)
        return context

    def _get_mock_bind_operation_context(self,
                                         device_owner=DEVICE_OWNER_COMPUTE):
        current = {'device_owner': device_owner}
        context = mock.Mock(current=current, _port=current,
                            segments_to_bind=self._get_segments_list())
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

    @classmethod
    def _get_mock_request_response(cls, status_code):
        response = mock.Mock(status_code=status_code)
        response.raise_for_status = mock.Mock() if status_code < 400 else (
            mock.Mock(side_effect=requests.exceptions.HTTPError(
                cls._status_code_msgs[status_code])))
        return response

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

    def _test_no_operation(self, method, context, status_code,
                           *args, **kwargs):
        request_response = self._get_mock_request_response(status_code)
        with mock.patch('requests.request',
                    return_value=request_response) as mock_method:
            method(context)
            assert not mock_method.called, ('Expected not to be called. '
                                       'Called %d times' % mock_method.calls)

    def _test_single_operation(self, method, context, status_code,
                               *args, **kwargs):
        request_response = self._get_mock_request_response(status_code)
        with mock.patch('requests.request',
                        return_value=request_response) as mock_method:
                method(context)
        mock_method.assert_called_once_with(
            headers=sdn_const.JSON_HTTP_HEADER,
            timeout=config.cfg.CONF.sdn.timeout,
            auth=AuthMatcher(),
            *args, **kwargs)

    def _test_create_resource_postcommit(self, object_type, status_code):
        method = getattr(self.mech, 'create_%s_postcommit' %
                         object_type.lower())
        context = self._get_mock_operation_context(object_type)
        url = '%s/%s' % (config.cfg.CONF.sdn.url, object_type)
        kwargs = {'url': url, 'data': DataMatcher(context, object_type)}
        self._test_single_operation(method, context, status_code,
                                    sdn_const.POST, **kwargs)

    def _test_update_resource_postcommit(self, object_type, status_code):
        method = getattr(self.mech, 'update_%s_postcommit' %
                         object_type.lower())
        context = self._get_mock_operation_context(object_type)
        url = '%s/%s/%s' % (config.cfg.CONF.sdn.url, object_type,
                            context.current['id'])
        kwargs = {'url': url, 'data': DataMatcher(context, object_type)}
        self._test_single_operation(method, context, status_code,
                                    sdn_const.PUT, **kwargs)

    def _test_delete_resource_postcommit(self, object_type, status_code):
        method = getattr(self.mech, 'delete_%s_postcommit' %
                         object_type.lower())
        context = self._get_mock_operation_context(object_type)
        url = '%s/%s/%s' % (config.cfg.CONF.sdn.url, object_type,
                            context.current['id'])
        kwargs = {'url': url, 'data': DataMatcher(context, object_type)}
        self._test_single_operation(method, context, status_code,
                                   sdn_const.DELETE, **kwargs)

    def _test_bind_port(self, status_code, context, assert_called=True):
        method = getattr(self.mech, 'bind_port')
        object_type = sdn_const.PORT_PATH
        url = '%s/%s' % (config.cfg.CONF.sdn.url, object_type)
        kwargs = {'url': url, 'data': DataMatcher(context, object_type)}

        if assert_called:
            self._test_single_operation(method, context, status_code,
                                        sdn_const.POST, **kwargs)
        else:
            self._test_no_operation(method, context, status_code,
                                    sdn_const.POST, **kwargs)

    def test_create_network_postcommit(self):
        for status_code in self._get_http_request_codes():
            self._test_create_resource_postcommit(sdn_const.NETWORK_PATH,
                                                  status_code,
                                                  )

    def test_update_port_postcommit(self):
        for status_code in self._get_http_request_codes():
            self._test_update_resource_postcommit(sdn_const.PORT_PATH,
                                                  status_code,
                                                  )

    def test_update_network_postcommit(self):
        for status_code in self._get_http_request_codes():
            self._test_update_resource_postcommit(sdn_const.NETWORK_PATH,
                                                  status_code,
                                                  )

    def test_delete_network_postcommit(self):
        for status_code in self._get_http_request_codes():
            self._test_delete_resource_postcommit(sdn_const.NETWORK_PATH,
                                                  status_code,
                                                  )

    def test_delete_port_postcommit(self):
        for status_code in self._get_http_request_codes():
            self._test_delete_resource_postcommit(sdn_const.PORT_PATH,
                                                  status_code,
                                                  )

    def test_bind_port_compute(self):
        """Bind port to VM

        SDN MD will call this kind of bind only
        The identify of this call is in port context
        The device_owner should be: "compute:None"
        """
        context = self._get_mock_bind_operation_context()
        for status_code in self._get_http_request_codes():
            self._test_bind_port(status_code, context)

    def test_bind_port_network(self):
        """Bind port network context

        bind network port can be occuer when a port binded to a dhcp
        SDN MD will filter such a calls
        """
        context = self._get_mock_bind_operation_context(
                                        neutron_const.DEVICE_OWNER_DHCP)
        for status_code in self._get_http_request_codes():
            self._test_bind_port(status_code, context, assert_called=False)

    def test_check_segment(self):
        """Validate the check_segment call."""
        segment = {'api.NETWORK_TYPE': ""}
        segment[api.NETWORK_TYPE] = constants.TYPE_VLAN
        self.assertTrue(self.mech.check_segment(segment))
        # Validate a network type not currently supported
        segment[api.NETWORK_TYPE] = constants.TYPE_LOCAL
        self.assertFalse(self.mech.check_segment(segment))
        segment[api.NETWORK_TYPE] = constants.TYPE_FLAT
        self.assertFalse(self.mech.check_segment(segment))
        segment[api.NETWORK_TYPE] = constants.TYPE_GRE
        self.assertFalse(self.mech.check_segment(segment))
        segment[api.NETWORK_TYPE] = constants.TYPE_VXLAN
        self.assertFalse(self.mech.check_segment(segment))
