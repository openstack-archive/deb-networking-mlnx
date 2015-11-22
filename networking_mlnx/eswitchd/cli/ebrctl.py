#!/usr/bin/python
# Copyright 2013 Mellanox Technologies, Ltd
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

import argparse
import sys

from networking_mlnx.eswitchd.cli import conn_utils
from networking_mlnx.eswitchd.cli import exceptions

client = conn_utils.ConnUtil()


def parse():
    """Main method that manages supported CLI commands.

    The actions that are supported throught the CLI are:
    write-sys, del-port, allocate-port and add-port
    Each action is matched with method that should handle it
    e.g. write-sys action is matched with  write_sys method
    """

    parser = argparse.ArgumentParser(prog='ebrctl')
    parser.add_argument('action', action='store_true')

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('vnic_mac')
    parent_parser.add_argument('device_id')
    parent_parser.add_argument('fabric')
    parent_parser.add_argument('vnic_type')
    subparsers = parser.add_subparsers()

    parser_add_port = subparsers.add_parser('add-port',
                                            parents=[parent_parser])
    parser_add_port.add_argument('dev_name')
    parser_add_port.set_defaults(func=add_port)

    parser_add_port = subparsers.add_parser('allocate-port',
                                            parents=[parent_parser])
    parser_add_port.set_defaults(func=allocate_port)

    parser_del_port = subparsers.add_parser('del-port')
    parser_del_port.set_defaults(func=del_port)
    parser_del_port.add_argument('fabric')
    parser_del_port.add_argument('vnic_mac')

    parser_write_sys = subparsers.add_parser('write-sys')
    parser_write_sys.set_defaults(func=write_sys)
    parser_write_sys.add_argument('path')
    parser_write_sys.add_argument('value')

    args = parser.parse_args()
    args.func(args)


def allocate_port(args):
    try:
        dev = client.allocate_nic(args.vnic_mac, args.device_id,
                                  args.fabric, args.vnic_type)
    except exceptions.MlxException as e:
        sys.stderr.write("Error in allocate command")
        sys.stderr.write(e.message)
        sys.exit(1)
    sys.stdout.write(dev)
    sys.exit(0)


def add_port(args):
    try:
        dev = client.plug_nic(args.vnic_mac, args.device_id, args.fabric,
                              args.vnic_type, args.dev_name)

    except exceptions.MlxException as e:
        sys.stderr.write("Error in add-port command")
        sys.stderr.write(e.message)
        sys.exit(1)
    sys.stdout.write(dev)
    sys.exit(0)


def del_port(args):
    try:
        client.deallocate_nic(args.vnic_mac, args.fabric)
    except exceptions.MlxException as e:
        sys.stderr.write("Error in del-port command")
        sys.stderr.write(e.message)
        sys.exit(1)
    sys.exit(0)


def write_sys(args):
    try:
        fd = open(args.path, 'w')
        fd.write(args.value)
        fd.close()
    except Exception as e:
        sys.stderr.write("Error in write-sys command")
        sys.stderr.write(e.message)
        sys.exit(1)
    sys.exit(0)


def main():
    parse()
