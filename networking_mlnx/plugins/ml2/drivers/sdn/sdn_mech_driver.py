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

from neutron.common import constants as neutron_const
from neutron.db import api as db_api
from neutron.objects.qos import policy as policy_object
from neutron.plugins.common import constants
from neutron.plugins.ml2 import driver_api as api
from oslo_log import log

from networking_mlnx._i18n import _LE
from networking_mlnx.journal import cleanup
from networking_mlnx.journal import journal
from networking_mlnx.journal import maintenance
from networking_mlnx.plugins.ml2.drivers.sdn import client
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
        except Exception as (e):
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
        self.client = client.SdnRestClient.create_client()
        self.journal = journal.SdnJournalThread()
        self._start_maintenance_thread()

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

    @context_validator(sdn_const.NETWORK)
    @error_handler
    def update_network_precommit(self, context):
        network_dic = context.current
        network_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, network_dic['id']))
        SDNMechanismDriver._record_in_journal(
            context, sdn_const.NETWORK, sdn_const.PUT, network_dic)

    def update_port_precommit(self, context):
        port_dic = context.current
        port_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, port_dic['network_id']))
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
        port_dic[NETWORK_QOS_POLICY] = (
            self._get_network_qos_policy(context, port_dic['network_id']))
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
                 sdn_const.PORT_DEVICE_OWNER_COMPUTE) or
                 device_owner == neutron_const.DEVICE_OWNER_DHCP))

    def check_segment(self, segment):
        """Verify if a segment is valid for the SDN MechanismDriver.

        Verify if the requested segment is supported by SDN MD and return True
        or False to indicate this to callers.
        """
        network_type = segment[api.NETWORK_TYPE]
        return network_type in [constants.TYPE_VLAN, constants.TYPE_FLAT]

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
