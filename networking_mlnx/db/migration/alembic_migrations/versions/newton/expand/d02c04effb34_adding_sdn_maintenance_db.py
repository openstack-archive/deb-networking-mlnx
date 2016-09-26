# Copyright 2016 Mellanox Technologies, Ltd
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

"""adding sdn maintenance db

Revision ID: d02c04effb34
Create Date: 2016-08-08 10:26:22.393410

"""

from alembic import op
from oslo_utils import uuidutils
import sqlalchemy as sa

from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const

# revision identifiers, used by Alembic.
revision = 'd02c04effb34'
down_revision = '9f30890cfbd1'


def upgrade():
    maint_table = op.create_table(
        'sdn_maintenance',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('state', sa.Enum(sdn_const.PENDING, sdn_const.PROCESSING,
                                   name='state'),
                  nullable=False),
        sa.Column('processing_operation', sa.String(70)),
        sa.Column('lock_updated', sa.TIMESTAMP, nullable=False,
                  server_default=sa.func.now(),
                  onupdate=sa.func.now())
    )
    # Insert the only row here that is used to synchronize the lock between
    # different Neutron processes.
    op.bulk_insert(maint_table,
                   [{'id': uuidutils.generate_uuid(),
                     'state': sdn_const.PENDING}])
