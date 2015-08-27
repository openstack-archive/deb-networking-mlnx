# Copyright 2015 Mellanox Technologies, Ltd
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
from neutron.tests.unit.agent.linux import test_dhcp

from networking_mlnx.dhcp import mlnx_dhcp


class TestMlnxDnsmasq(test_dhcp.TestDnsmasq):

    def _get_dnsmasq(self, network, process_monitor=None):
        process_monitor = process_monitor or mock.Mock()
        return mlnx_dhcp.MlnxDnsmasq(self.conf, network,
                            process_monitor=process_monitor)

    def test_only_populates_dhcp_enabled_subnet_on_a_network(self):
        exp_host_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/host'
        exp_host_data = ('00:00:80:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:00:'
                         '00:aa:bb:cc,host-192-168-0-2.openstacklocal.,'
                         '192.168.0.2\n'
                         '00:00:f3:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:f3:00:'
                         '00:aa:bb:cc,host-192-168-0-3.openstacklocal.,'
                         '192.168.0.3\n'
                         '00:00:0f:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:aa:bb:cc,host-192-168-0-4.openstacklocal.,'
                         '192.168.0.4\n'
                         '00:00:0f:rr:rr:rr,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:rr:rr:rr,host-192-168-0-1.openstacklocal.,'
                         '192.168.0.1\n').lstrip()
        dm = self._get_dnsmasq(test_dhcp.FakeDualNetworkSingleDHCP())
        dm._output_hosts_file()
        self.safe.assert_has_calls([mock.call(exp_host_name,
                                              exp_host_data)])

    @property
    def _test_no_dhcp_domain_alloc_data(self):
        exp_host_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/host'
        exp_host_data = ('00:00:80:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:00:'
                         '00:aa:bb:cc,host-192-168-0-2,'
                         '192.168.0.2\n'
                         '00:00:f3:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:f3:00:'
                         '00:aa:bb:cc,host-fdca-3ba5-a17a-4ba3--2,'
                         '[fdca:3ba5:a17a:4ba3::2]\n'
                         '00:00:0f:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:aa:bb:cc,host-192-168-0-3,'
                         '192.168.0.3\n'
                         '00:00:0f:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:aa:bb:cc,host-fdca-3ba5-a17a-4ba3--3,'
                         '[fdca:3ba5:a17a:4ba3::3]\n'
                         '00:00:0f:rr:rr:rr,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:rr:rr:rr,host-192-168-0-1,'
                         '192.168.0.1\n').lstrip()
        exp_addn_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/addn_hosts'
        exp_addn_data = (
            '192.168.0.2\t'
            'host-192-168-0-2 host-192-168-0-2\n'
            'fdca:3ba5:a17a:4ba3::2\t'
            'host-fdca-3ba5-a17a-4ba3--2 '
            'host-fdca-3ba5-a17a-4ba3--2\n'
            '192.168.0.3\thost-192-168-0-3 '
            'host-192-168-0-3\n'
            'fdca:3ba5:a17a:4ba3::3\t'
            'host-fdca-3ba5-a17a-4ba3--3 '
            'host-fdca-3ba5-a17a-4ba3--3\n'
            '192.168.0.1\t'
            'host-192-168-0-1 '
            'host-192-168-0-1\n'
        ).lstrip()
        return (exp_host_name, exp_host_data,
                exp_addn_name, exp_addn_data)

    @property
    def _test_reload_allocation_data(self):
        exp_host_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/host'
        exp_host_data = ('00:00:80:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:00:'
                         '00:aa:bb:cc,host-192-168-0-2.openstacklocal.,'
                         '192.168.0.2\n'
                         '00:00:f3:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:f3:00:'
                         '00:aa:bb:cc,host-fdca-3ba5-a17a-4ba3--2.'
                         'openstacklocal.,[fdca:3ba5:a17a:4ba3::2]\n'
                         '00:00:0f:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:aa:bb:cc,host-192-168-0-3.openstacklocal.,'
                         '192.168.0.3\n'
                         '00:00:0f:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:aa:bb:cc,host-fdca-3ba5-a17a-4ba3--3.'
                         'openstacklocal.,[fdca:3ba5:a17a:4ba3::3]\n'
                         '00:00:0f:rr:rr:rr,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:'
                         '00:rr:rr:rr,host-192-168-0-1.openstacklocal.,'
                         '192.168.0.1\n').lstrip()
        exp_addn_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/addn_hosts'
        exp_addn_data = (
            '192.168.0.2\t'
            'host-192-168-0-2.openstacklocal. host-192-168-0-2\n'
            'fdca:3ba5:a17a:4ba3::2\t'
            'host-fdca-3ba5-a17a-4ba3--2.openstacklocal. '
            'host-fdca-3ba5-a17a-4ba3--2\n'
            '192.168.0.3\thost-192-168-0-3.openstacklocal. '
            'host-192-168-0-3\n'
            'fdca:3ba5:a17a:4ba3::3\t'
            'host-fdca-3ba5-a17a-4ba3--3.openstacklocal. '
            'host-fdca-3ba5-a17a-4ba3--3\n'
            '192.168.0.1\t'
            'host-192-168-0-1.openstacklocal. '
            'host-192-168-0-1\n'
        ).lstrip()
        exp_opt_name = '/dhcp/cccccccc-cccc-cccc-cccc-cccccccccccc/opts'
        fake_v6 = '2001:0200:feed:7ac0::1'
        exp_opt_data = (
            'tag:tag0,option:dns-server,8.8.8.8\n'
            'tag:tag0,option:classless-static-route,20.0.0.1/24,20.0.0.1,'
            '169.254.169.254/32,192.168.0.1,0.0.0.0/0,192.168.0.1\n'
            'tag:tag0,249,20.0.0.1/24,20.0.0.1,'
            '169.254.169.254/32,192.168.0.1,0.0.0.0/0,192.168.0.1\n'
            'tag:tag0,option:router,192.168.0.1\n'
            'tag:tag1,option6:dns-server,%s\n'
            'tag:tag1,option6:domain-search,openstacklocal').lstrip() % (
            '[' + fake_v6 + ']')
        return (exp_host_name, exp_host_data,
                exp_addn_name, exp_addn_data,
                exp_opt_name, exp_opt_data,)

    def test_release_unused_leases_one_lease_with_client_id(self):
        dnsmasq = self._get_dnsmasq(test_dhcp.FakeDualNetwork())

        ip1 = '192.168.0.2'
        mac1 = '00:00:80:aa:bb:cc'
        client_id1 = ('ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:'
                      '00:00:aa:bb:cc')
        ip2 = '192.168.0.5'
        mac2 = '00:00:0f:aa:bb:55'
        client_id2 = ('ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:'
                      '00:00:aa:bb:55')

        old_leases = set([(ip1, mac1, client_id1), (ip2, mac2, client_id2)])
        dnsmasq._read_hosts_file_leases = mock.Mock(return_value=old_leases)
        dnsmasq._output_hosts_file = mock.Mock()
        dnsmasq._release_lease = mock.Mock()
        dnsmasq.network.ports = [test_dhcp.FakePort5()]

        dnsmasq._release_unused_leases()

        dnsmasq._release_lease.assert_called_once_with(
            mac1, ip1, client_id1)

    def test_only_populates_dhcp_client_id(self):
        exp_host_name = '/dhcp/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/host'
        exp_host_data = ('00:00:80:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:'
                         '00:00:aa:bb:cc,host-192-168-0-2.openstacklocal.,'
                         '192.168.0.2\n'
                         '00:00:0f:aa:bb:55,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:'
                         '00:00:aa:bb:55,host-192-168-0-5.openstacklocal.,'
                         '192.168.0.5\n'
                         '00:00:0f:aa:bb:66,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:'
                         '00:00:aa:bb:66,host-192-168-0-6.openstacklocal.,'
                         '192.168.0.6,'
                         'set:ccccccccc-cccc-cccc-cccc-ccccccccc\n').lstrip()

        dm = self._get_dnsmasq(test_dhcp.FakeV4NetworkClientId)
        dm._output_hosts_file()
        self.safe.assert_has_calls([mock.call(exp_host_name,
                                              exp_host_data)])

    def test_host_and_opts_file_on_net_with_V6_stateless_and_V4_subnets(
                                                                    self):
        exp_host_name = '/dhcp/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/host'
        exp_host_data = (
            '00:16:3e:c2:77:1d,set:hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh\n'
            '00:16:3e:c2:77:1d,'
            'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:16:3e:00:00:c2:77:1d,'
            'host-192-168-0-3.openstacklocal.,'
            '192.168.0.3,set:hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh\n'
            '00:00:0f:rr:rr:rr,'
            'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:00:00:rr:rr:rr,'
            'host-192-168-0-1.openstacklocal.,192.168.0.1\n').lstrip()
        exp_opt_name = '/dhcp/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/opts'
        exp_opt_data = (
            'tag:tag0,option6:domain-search,openstacklocal\n'
            'tag:tag1,option:dns-server,8.8.8.8\n'
            'tag:tag1,option:classless-static-route,20.0.0.1/24,20.0.0.1,'
            '169.254.169.254/32,192.168.0.1,0.0.0.0/0,192.168.0.1\n'
            'tag:tag1,249,20.0.0.1/24,20.0.0.1,169.254.169.254/32,'
            '192.168.0.1,0.0.0.0/0,192.168.0.1\n'
            'tag:tag1,option:router,192.168.0.1\n'
            'tag:hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh,'
            'option6:dns-server,ffea:3ba5:a17a:4ba3::100').lstrip()

        dm = self._get_dnsmasq(
            test_dhcp.FakeNetworkWithV6SatelessAndV4DHCPSubnets())
        dm._output_hosts_file()
        dm._output_opts_file()
        self.safe.assert_has_calls([mock.call(exp_host_name, exp_host_data),
                                    mock.call(exp_opt_name, exp_opt_data)])

    def test_only_populates_dhcp_enabled_subnets(self):
        exp_host_name = '/dhcp/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee/host'
        exp_host_data = ('00:00:80:aa:bb:cc,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:80:'
                         '00:00:aa:bb:cc,host-192-168-0-2.openstacklocal.,'
                         '192.168.0.2\n'
                         '00:16:3E:C2:77:1D,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:16:3E:'
                         '00:00:C2:77:1D,host-192-168-0-4.openstacklocal.,'
                         '192.168.0.4\n'
                         '00:00:0f:rr:rr:rr,'
                         'id:ff:00:00:00:00:00:02:00:00:02:c9:00:00:00:0f:'
                         '00:00:rr:rr:rr,host-192-168-0-1.openstacklocal.,'
                         '192.168.0.1\n').lstrip()
        dm = self._get_dnsmasq(test_dhcp.FakeDualStackNetworkSingleDHCP())
        dm._output_hosts_file()
        self.safe.assert_has_calls([mock.call(exp_host_name,
                                              exp_host_data)])

    def test_release_unused_leases_one_lease(self):
        pass
