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

from neutron_lib.db import model_base
import sqlalchemy as sa

from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const


class SdnMaintenance(model_base.BASEV2, model_base.HasId):
    __tablename__ = 'sdn_maintenance'

    state = sa.Column(sa.Enum(sdn_const.PENDING, sdn_const.PROCESSING),
                      nullable=False)
    processing_operation = sa.Column(sa.String(70))
    lock_updated = sa.Column(sa.TIMESTAMP, nullable=False,
                             server_default=sa.func.now(),
                             onupdate=sa.func.now())
