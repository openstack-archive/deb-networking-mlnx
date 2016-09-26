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


class SdnJournal(model_base.BASEV2, model_base.HasId):
    __tablename__ = 'sdn_journal'

    object_type = sa.Column(sa.String(36), nullable=False)
    object_uuid = sa.Column(sa.String(36), nullable=False)
    operation = sa.Column(sa.String(36), nullable=False)
    data = sa.Column(sa.Text, nullable=True)
    job_id = sa.Column(sa.String(36), nullable=True)
    state = sa.Column(sa.Enum(sdn_const.PENDING, sdn_const.FAILED,
                              sdn_const.PROCESSING, sdn_const.MONITORING,
                              sdn_const.COMPLETED),
                      nullable=False, default=sdn_const.PENDING)
    retry_count = sa.Column(sa.Integer, default=0)
    created_at = sa.Column(sa.DateTime, server_default=sa.func.now())
    last_retried = sa.Column(sa.TIMESTAMP, server_default=sa.func.now(),
                             onupdate=sa.func.now())
