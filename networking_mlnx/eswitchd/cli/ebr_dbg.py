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

from __future__ import print_function
import sys

from networking_mlnx.eswitchd.cli import conn_utils
from networking_mlnx.eswitchd.cli import exceptions

action = sys.argv[1]
client = conn_utils.ConnUtil()


def pprint_table(out, table):
    """Prints out a table of data, padded for alignment

    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns.
    """

    def get_max_width(table, index):
        """Get the maximum width of the given column index"""
        return max([len(str(row[index])) for row in table])

    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print(row[0].ljust(col_paddings[0] + 1), file=out)
        # rest of the cols
        for i in range(1, len(row)):
            col = str(row[i]).rjust(col_paddings[i] + 2)
            print(col, file=out)
        print(file=out)


def main():
    if action == 'get-tables':
        fabric = sys.argv[2]
        try:
            result = client.get_tables(fabric)
            for fabric, tables in result.items():
                print("FABRIC = %s" % fabric)
                print("========================")
                for table, data in tables.items():
                    print("TABLE: %s" % table)
                    pprint_table(sys.stdout, data)
                    print("========================")
        except exceptions.MlxException as e:
            sys.stderr.write("Error in get-tables command")
            sys.stderr.write(e.message)
            sys.exit(1)
        sys.exit(0)

if __name__ == '__main__':
    main()
