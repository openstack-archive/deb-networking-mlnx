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

import functools


from neutron.db import api as db_api
from neutron.objects.qos import policy as policy_object
from neutron.plugins.common import constants
from neutron.plugins.ml2 import driver_api as api
from neutron_lib.api.definitions import portbindings
from neutron_lib import constants as neutron_const
from oslo_log import log

from networking_mlnx._i18n import _LE
from networking_mlnx.journal import cleanup
from networking_mlnx.journal import journal
from networking_mlnx.journal import maintenance
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const

LOG = log.getLogger(__name__)

NETWORK_QOS_POLICY = 'network_qos_policy'


def context_validator(context_type=None):
    def real_decorator(func):
        @functools.wraps(func)
        def wrapper(instance, context, *args, **kwargs):
            if context_type == sdn_const.PORT:
                # port context contain network_context
                # which include the segments
                segments = getattr(context._network_context, "_segments", None)
            elif context_type == sdn_const.NETWORK:
                segments = getattr(context, "_segments", None)
            else:
                segments = getattr(context, "segments_to_bind", None)
            if segments and getattr(instance, "check_segments", None):
                if instance.check_segments(segments):
                    return func(instance, context, *args, **kwargs)
        return wrapper
    return real_decorator


def error_handler(func):
    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        try:
            return func(instance, *args, **kwargs)
        except Exception as e:
            LOG.error(
                    _LE("%(function_name)s %(exception_desc)s"),
                    {'function_name': func.__name__,
                    'exception_desc': str(e)}
            )
    return wrapper


class SDNMechanismDriver(api.MechanismDriver):

    """Mechanism Driver for SDN.

    This driver send notifications to SDN provider.
    The notifications are for port/network changes.
    """

    def initialize(self):
        self.journal = journal.SdnJournalThread()
        self._start_maintenance_thread()
        self.supported_vnic_types = [portbindings.VNIC_BAREMETAL]
        self.supported_network_types = (
            [constants.TYPE_VLAN, constants.TYPE_FLAT])
        self.vif_type = portbindings.VIF_TYPE_OTHER
        self.vif_details = {}

    def _start_maintenance_thread(self):
        # start the maintenance thread and register all the maintenance
        # operations :
        # (1) JournalCleanup - Delete completed rows from journal
        # (2) CleanupProcessing - Mark orphaned processing rows to pending
        cleanup_obj = cleanup.JournalCleanup()
        self._maintenance_thread = maintenance.MaintenanceThread()
        self._maintenance_thread.register_operation(
            cleanup_obj.delete_completed_rows)
        self._maintenance_thread.register_operation(
            cleanup_obj.cleanup_processing_rows)
        self._maintenance_thread.start()

    @staticmethod
    def _record_in_journal(context, object_type, operation, data=None):
        if data is None:
            data = context.current
        journal.record(context._plugin_context.session, object_type,
                       context.current['id'], operation, data)

    @context_validator(sdn_const.NETWORK)
    @error_handler
    def create_network_precommit(self, context):
        network_dic = context.current
        if network_dic.get('provider:segmentation_id'):
            network_dic[NETWORK_QOS_POLICY] = (
                self._get_network_qos_policy(context, network_dic['id']))
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.NETWORK, sdn_const.POST, network_dic)

    @context_validator()
    @error_handler
    def bind_port(self, context):
        port_dic = context.current
        if self._is_send_bind_port(port_dic):
            port_dic[NETWORK_QOS_POLICY] = (
                self._get_network_qos_policy(context, port_dic['network_id']))
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.PORT, sdn_const.POST, port_dic)

        segments = context.network.network_segments
        for segment in segments:
            vnic_type = port_dic[portbindings.VNIC_TYPE]
            # set port to active if it is in the supported vnic types
            # currently used for VNIC_BAREMETAL
            if vnic_type in self.supported_vnic_types:
                context.set_binding(segment[api.ID],
                                    self.vif_type,
                                    self.vif_details)

    @context_validator(sdn_const.NETWORK)
    @error_handler
    def update_network_precommit(self, context):
        network_dic = context.current
        network_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, network_dic['id']))
        SDNMechanismDriver._record_in_journal(
            context, sdn_const.NETWORK, sdn_const.PUT, network_dic)

    def _get_client_id_from_port(self, port):
        dhcp_opts = port.get('extra_dhcp_opts', [])
        for dhcp_opt in dhcp_opts:
            if (isinstance(dhcp_opt, dict) and
                    dhcp_opt.get('opt_name') == 'client-id'):
                return dhcp_opt.get('opt_value')

    def _get_local_link_information(self, port):
        binding_profile = port.get('binding:profile')
        if binding_profile:
            return binding_profile.get('local_link_information')

    def create_port_precommit(self, context):
        port_dic = context.current
        port_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, port_dic['network_id']))

        vnic_type = port_dic[portbindings.VNIC_TYPE]
        if (vnic_type == portbindings.VNIC_BAREMETAL and
            (self._get_client_id_from_port(port_dic) or
             self._get_local_link_information(port_dic))):
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.PORT, sdn_const.POST, port_dic)

    def update_port_precommit(self, context):
        port_dic = context.current
        orig_port_dict = context.original
        port_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, port_dic['network_id']))

        vnic_type = port_dic[portbindings.VNIC_TYPE]
        # Check if we get a client id after binding the bare metal port,
        # and report the port to neo
        if vnic_type == portbindings.VNIC_BAREMETAL:
            # Ethernet Case
            link__info = self._get_local_link_information(port_dic)
            orig_link_info = self._get_local_link_information(orig_port_dict)
            if link__info != orig_link_info:
                SDNMechanismDriver._record_in_journal(
                    context, sdn_const.PORT, sdn_const.POST, port_dic)
                return
            # InfiniBand Case
            current_client_id = self._get_client_id_from_port(port_dic)
            orig_client_id = self._get_client_id_from_port(orig_port_dict)
            if current_client_id != orig_client_id:
                SDNMechanismDriver._record_in_journal(
                    context, sdn_const.PORT, sdn_const.POST, port_dic)
        # delete the port in case instance is deleted
        # and port is created separately
        elif (orig_port_dict[portbindings.HOST_ID] and
              not port_dic[portbindings.HOST_ID] and
              self._is_send_bind_port(orig_port_dict)):
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.PORT, sdn_const.DELETE, orig_port_dict)
        # delete the port in case instance is migrated to another hypervisor
        elif (orig_port_dict[portbindings.HOST_ID] and
              port_dic[portbindings.HOST_ID] !=
              orig_port_dict[portbindings.HOST_ID] and
              self._is_send_bind_port(orig_port_dict)):
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.PORT, sdn_const.DELETE, orig_port_dict)
        else:
            SDNMechanismDriver._record_in_journal(
                context, sdn_const.PORT, sdn_const.PUT, port_dic)

    @context_validator(sdn_const.NETWORK)
    @error_handler
    def delete_network_precommit(self, context):
        network_dic = context.current
        network_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, network_dic['id']))
        SDNMechanismDriver._record_in_journal(
            context, sdn_const.NETWORK, sdn_const.DELETE, data=network_dic)

    @context_validator(sdn_const.PORT)
    @error_handler
    def delete_port_precommit(self, context):
        port_dic = context.current
        # delete the port only if attached to a host
        if port_dic[portbindings.HOST_ID]:
                port_dic[NETWORK_QOS_POLICY] = (
                    self._get_network_qos_policy(context,
                                                 port_dic['network_id']))
                SDNMechanismDriver._record_in_journal(
                    context, sdn_const.PORT, sdn_const.DELETE, port_dic)

    @journal.call_thread_on_end
    def sync_from_callback(self, operation, res_type, res_id, resource_dict):
        object_type = res_type.singular
        object_uuid = (resource_dict[object_type]['id']
                       if operation == sdn_const.POST else res_id)
        if resource_dict is not None:
            resource_dict = resource_dict[object_type]
        journal.record(db_api.get_session(), object_type, object_uuid,
                       operation, resource_dict)

    def _postcommit(self, context):
        self.journal.set_sync_event()

    create_network_postcommit = _postcommit
    update_network_postcommit = _postcommit
    create_port_postcommit = _postcommit
    update_port_postcommit = _postcommit
    delete_network_postcommit = _postcommit
    delete_port_postcommit = _postcommit

    def _is_send_bind_port(self, port_context):
        """Verify that bind port is occur in compute context

        The request HTTP will occur only when the device owner is compute
        or dhcp.
        """
        device_owner = port_context['device_owner']
        return (device_owner and
                (device_owner.lower().startswith(
                 neutron_const.DEVICE_OWNER_COMPUTE_PREFIX) or
                 device_owner == neutron_const.DEVICE_OWNER_DHCP))

    def check_segment(self, segment):
        """Verify if a segment is valid for the SDN MechanismDriver.

        Verify if the requested segment is supported by SDN MD and return True
        or False to indicate this to callers.
        """
        network_type = segment[api.NETWORK_TYPE]
        return network_type in self.supported_network_types

    def check_segments(self, segments):
        """Verify if there is a segment in a list of segments that valid for
         the SDN MechanismDriver.

        Verify if the requested segments are supported by SDN MD and return
        True or False to indicate this to callers.
        """
        if segments:
            for segment in segments:
                if self.check_segment(segment):
                    return True
        return False

    def _get_network_qos_policy(self, context, net_id):
        return policy_object.QosPolicy.get_network_policy(
            context._plugin_context, net_id)
