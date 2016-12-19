# Copyright 2014 Mellanox Technologies, Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from oslo_config import cfg
from oslo_config import fixture as fixture_config

from networking_mlnx.plugins.ml2.drivers.sdn import client
from networking_mlnx.plugins.ml2.drivers.sdn import config
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const
from networking_mlnx.tests import base


class TestClient(base.TestCase):

    def setUp(self):
        super(TestClient, self).setUp()
        self.conf_fixture = self.useFixture(fixture_config.Config())
        self.conf = self.conf_fixture.conf
        self.conf.register_opts(config.sdn_opts, sdn_const.GROUP_OPT)
        self._set_args()
        self.client = client.SdnRestClient.create_client()
        self.url = 'some_url'
        self.data = {'some': 'data'}

    def _set_args(self):
        self.conf.register_opts(config.sdn_opts, sdn_const.GROUP_OPT)
        for arg in client.SdnRestClient.MANDATORY_ARGS:
            self.conf.set_override(name=arg,
                                   override="http://some_val",
                                   group=sdn_const.GROUP_OPT)

    def test_mandatory_args(self):
        mandatory_arg_objects = filter(
                lambda obj: obj.name in client.SdnRestClient.MANDATORY_ARGS,
                config.sdn_opts)
        for arg in mandatory_arg_objects:
            self._set_args()
            self.conf.unregister_opt(opt=arg,
                                     group=sdn_const.GROUP_OPT)
            self.assertRaises(cfg.NoSuchOptError,
                              client.SdnRestClient.create_client)

    @mock.patch('networking_mlnx.plugins.ml2.drivers.'
                'sdn.client.SdnRestClient.request')
    def test_get(self, mocked_request):
        self.client.get(self.url, self.data)
        expected_url = '/'.join((self.conf.sdn.url, self.url))
        mocked_request.assert_called_once_with(sdn_const.GET,
                                               expected_url,
                                               self.data)

        mocked_request.reset_mock()
        self.client.get(self.url)
        mocked_request.assert_called_once_with(sdn_const.GET,
                                               expected_url,
                                               None)

        mocked_request.reset_mock()
        self.client.get()
        mocked_request.assert_called_once_with(sdn_const.GET,
                                               self.conf.sdn.url,
                                               None)

    @mock.patch('networking_mlnx.plugins.ml2.drivers.'
                'sdn.client.SdnRestClient.request')
    def test_put(self, mocked_request):
        self.client.put(self.url, self.data)
        expected_url = '/'.join((self.conf.sdn.url,
                                 self.conf.sdn.domain,
                                 self.url))
        mocked_request.assert_called_once_with(sdn_const.PUT,
                                               expected_url,
                                               self.data)

        mocked_request.reset_mock()
        self.client.put(self.url)
        mocked_request.assert_called_once_with(sdn_const.PUT,
                                               expected_url,
                                               None)

        mocked_request.reset_mock()
        self.client.put()
        expected_url = '/'.join((self.conf.sdn.url, self.conf.sdn.domain))
        mocked_request.assert_called_once_with(sdn_const.PUT,
                                               expected_url,
                                               None)

    @mock.patch('networking_mlnx.plugins.ml2.drivers.'
                'sdn.client.SdnRestClient.request')
    def test_post(self, mocked_request):
        self.client.post(self.url, self.data)
        expected_url = '/'.join((self.conf.sdn.url,
                                 self.conf.sdn.domain,
                                 self.url))
        mocked_request.assert_called_once_with(sdn_const.POST,
                                               expected_url,
                                               self.data)

        mocked_request.reset_mock()
        self.client.post(self.url)
        mocked_request.assert_called_once_with(sdn_const.POST,
                                               expected_url,
                                               None)

        mocked_request.reset_mock()
        self.client.post()
        expected_url = '/'.join((self.conf.sdn.url, self.conf.sdn.domain))
        mocked_request.assert_called_once_with(sdn_const.POST,
                                               expected_url,
                                               None)

    @mock.patch('networking_mlnx.plugins.ml2.drivers.'
                'sdn.client.SdnRestClient.request')
    def test_delete(self, mocked_request):
        self.client.delete(self.url, self.data)
        expected_url = '/'.join((self.conf.sdn.url,
                                 self.conf.sdn.domain,
                                 self.url))
        mocked_request.assert_called_once_with(sdn_const.DELETE,
                                               expected_url,
                                               self.data)

        mocked_request.reset_mock()
        self.client.delete(self.url)
        mocked_request.assert_called_once_with(sdn_const.DELETE,
                                               expected_url,
                                               None)

        mocked_request.reset_mock()
        self.client.delete()
        expected_url = '/'.join((self.conf.sdn.url, self.conf.sdn.domain))
        mocked_request.assert_called_once_with(sdn_const.DELETE,
                                               expected_url,
                                               None)

    @mock.patch('networking_mlnx.plugins.ml2.drivers.'
                'sdn.client.SdnRestClient._get_session',
                return_value=mock.Mock())
    def test_request_bad_data(self, mocked_get_session):
        # non serialized json data
        data = self
        self.assertRaises(ValueError,
                          self.client.request,
                          sdn_const.DELETE, '', data)
