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

"""adding sdn journal db

Revision ID: 9f30890cfbd1
Create Date: 2016-08-07 10:57:15.895551

"""

from alembic import op
import sqlalchemy as sa

from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const

# revision identifiers, used by Alembic.
revision = '9f30890cfbd1'
down_revision = '65b6db113427b9'


def upgrade():
    op.create_table(
        'sdn_journal',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('object_type', sa.String(length=36), nullable=False),
        sa.Column('object_uuid', sa.String(length=36), nullable=False),
        sa.Column('operation', sa.String(length=36), nullable=False),
        sa.Column('data', sa.PickleType(), nullable=True),
        sa.Column('job_id', sa.String(length=36), nullable=True),
        sa.Column('state',
                  sa.Enum(sdn_const.PENDING, sdn_const.FAILED,
                          sdn_const.PROCESSING, sdn_const.COMPLETED,
                          name='state'),
                  nullable=False, default=sdn_const.PENDING),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('last_retried', sa.TIMESTAMP, server_default=sa.func.now(),
                  onupdate=sa.func.now())
    )
