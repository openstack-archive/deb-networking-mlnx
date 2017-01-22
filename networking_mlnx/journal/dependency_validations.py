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

from oslo_serialization import jsonutils

from networking_mlnx.db import db
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const


def _is_valid_operation(session, row):
    # Check if there are older updates in the queue
    if db.check_for_older_ops(session, row):
        return False
    return True


def validate_network_operation(session, row):
    """Validate the network operation based on dependencies.

    Validate network operation depending on whether it's dependencies
    are still in 'pending' or 'processing' state. e.g.
    """
    if row.operation == sdn_const.DELETE:
        # Check for any pending or processing create or update
        # ops on this uuid itself
        if db.check_for_pending_or_processing_ops(
            session, row.object_uuid, [sdn_const.PUT,
                                       sdn_const.POST]):
            return False
        if db.check_for_pending_delete_ops_with_parent(
            session, sdn_const.PORT, row.object_uuid):
            return False
    elif (row.operation == sdn_const.PUT and
            not _is_valid_operation(session, row)):
        return False
    return True


def validate_port_operation(session, row):
    """Validate port operation based on dependencies.

    Validate port operation depending on whether it's dependencies
    are still in 'pending' or 'processing' state. e.g.
    """
    if row.operation in (sdn_const.POST, sdn_const.PUT):
        network_dict = jsonutils.loads(row.data)
        network_id = network_dict['network_id']
        # Check for pending or processing network operations
        ops = db.check_for_pending_or_processing_ops(
            session, network_id, [sdn_const.POST])
        if ops:
            return False
    return _is_valid_operation(session, row)


_VALIDATION_MAP = {
    sdn_const.NETWORK: validate_network_operation,
    sdn_const.PORT: validate_port_operation,
}


def validate(session, row):
    """Validate resource dependency in journaled operations.

    :param session: db session
    :param row: entry in journal entry to be validated
    """
    return _VALIDATION_MAP[row.object_type](session, row)


def register_validator(object_type, validator):
    """Register validator function for given resource.

    :param object_type: neutron resource type
    :param validator: function to be registered which validates resource
         dependencies
    """
    assert object_type not in _VALIDATION_MAP
    _VALIDATION_MAP[object_type] = validator
