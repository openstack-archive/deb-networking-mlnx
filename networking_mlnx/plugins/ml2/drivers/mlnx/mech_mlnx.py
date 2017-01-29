# Copyright (c) 2014 OpenStack Foundation
# All Rights Reserved.
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

from neutron.api.v2 import attributes
from neutron.plugins.common import constants as p_constants
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers import mech_agent
from neutron_lib.api.definitions import extra_dhcp_opt as edo_ext
from neutron_lib.api.definitions import portbindings
from neutron_lib.plugins import directory
from oslo_config import cfg

from networking_mlnx.plugins.ml2.drivers.mlnx import config  # noqa

AGENT_TYPE_MLNX = 'Mellanox plugin agent'
VIF_TYPE_IB_HOSTDEV = 'ib_hostdev'


class MlnxMechanismDriver(mech_agent.SimpleAgentMechanismDriverBase):
    """Attach to networks using Mellanox eSwitch L2 agent.

    The MellanoxMechanismDriver integrates the ml2 plugin with the
    Mellanox eswitch L2 agent. Port binding with this driver requires the
    Mellanox eswitch  agent to be running on the port's host, and that agent
    to have connectivity to at least one segment of the port's
    network.
    """

    def __init__(self):
        super(MlnxMechanismDriver, self).__init__(
            agent_type=AGENT_TYPE_MLNX,
            vif_type=VIF_TYPE_IB_HOSTDEV,
            vif_details={portbindings.CAP_PORT_FILTER: False},
            supported_vnic_types=[portbindings.VNIC_DIRECT])

    def get_allowed_network_types(self, agent=None):
        return [p_constants.TYPE_LOCAL, p_constants.TYPE_FLAT,
                p_constants.TYPE_VLAN]

    def get_mappings(self, agent):
        return agent['configurations'].get('interface_mappings', {})

    def try_to_bind_segment_for_agent(self, context, segment, agent):
        if self.check_segment_for_agent(segment, agent):
            if (segment[api.NETWORK_TYPE] in
                    (p_constants.TYPE_FLAT, p_constants.TYPE_VLAN)):
                self.vif_details['physical_network'] = segment[
                    'physical_network']
            context.set_binding(segment[api.ID],
                                self.vif_type,
                                self.vif_details)

    def _gen_client_id(self, port):
        _PREFIX = 'ff:00:00:00:00:00:02:00:00:02:c9:00:'
        _MIDDLE = ':00:00:'
        mac_address = port["mac_address"]
        mac_first = mac_address[:8]
        mac_last = mac_address[9:]
        client_id = ''.join([_PREFIX, mac_first, _MIDDLE, mac_last])
        return client_id

    def _gen_client_id_opt(self, port):
        client_id = self._gen_client_id(port)
        return [{"opt_name": edo_ext.DHCP_OPT_CLIENT_ID,
                 "opt_value": client_id}]

    def _gen_none_client_id_opt(self, port):
        updated_extra_dhcp_opts = []
        for opt in port["extra_dhcp_opts"]:
            opt["opt_value"] = None
            updated_extra_dhcp_opts.append(opt)
        return updated_extra_dhcp_opts

    def _process_port_info(self, context):
        original_port = context.original
        updated_port = context.current
        original_host_id = original_port.get("binding:host_id")
        current_host_id = updated_port.get("binding:host_id")
        # in case migration did not take place or delete port
        if original_host_id == current_host_id or current_host_id is None:
            return

        plugin = directory.get_plugin()
        # if host_id was empty
        if not original_port.get("binding:host_id"):
            print(updated_port)
            # if port doesn't have extra_dhcp_opts
            if (not updated_port.get("extra_dhcp_opts") and
                "compute" in updated_port["device_owner"] and
                updated_port["binding:vnic_type"] in ("direct", "normal")):
                updated_port["extra_dhcp_opts"] = \
                    self._gen_client_id_opt(updated_port)
        else:
            if original_port.get("extra_dhcp_opts"):
                updated_port["extra_dhcp_opts"] = \
                    self._gen_none_client_id_opt(updated_port)
        plugin._update_extra_dhcp_opts_on_port(
            context._plugin_context,
            updated_port["id"],
            {attributes.PORT: updated_port})

    def update_port_precommit(self, context):
        if cfg.CONF.MLNX_IB.update_client_id:
            self._process_port_info(context)
