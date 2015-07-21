# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
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

import unittest2

from fuel_agent.drivers.dynamic import adapters
from fuel_agent.drivers.dynamic import parser
from fuel_agent import objects


class BaseParsingTestCase(unittest2.TestCase):

    def get_parser(self, partition_data, node=None):
        if node is None:
            node = parser.Node()

        return parser.DynamicPartitionFormat(partition_data, node)


class TestParseMD(BaseParsingTestCase):

    def test_parse_md(self):
        partition_data = {
            'mds': [{
                'id': 1,
                'name': 'some-raid',
                'level': '1',
                'devices': [
                    '/dev/sda',
                    '/dev/sdb',
                ],
                'spares': [
                    '/dev/sdc',
                    '/dev/sdd',
                ]
            }]
        }
        parser = self.get_parser(partition_data)
        parsed_mds = parser.parse_mds()
        assert len(parsed_mds) == 1
        md = parsed_mds[0]
        assert isinstance(md, objects.MD)

        assert md.name == 'some-raid'
        assert md.level == '1'
        self.assertItemsEqual(
            md.devices,
            ['/dev/sda', '/dev/sdb']
        )
        self.assertItemsEqual(
            md.spares,
            ['/dev/sdc', '/dev/sdd']
        )

    def test_parse_duplicated_md_ids(self):
        partition_data = {
            'mds': [{
                'id': 1,
                'name': 'some-raid',
                'level': '1',
                'devices': [
                    '/dev/sda',
                ],
                'spares': [
                    '/dev/sdd',
                ]},
                {
                'id': 1,
                'name': 'some-raid',
                'level': '1',
                'devices': [
                    '/dev/sde',
                ],
                'spares': [
                    '/dev/sdc',
                ]
            }]
        }
        dynamic_parser = self.get_parser(partition_data)
        with self.assertRaisesRegexp(parser.ParserError,
                                     "Duplicated ID 1 for MD object"):
            dynamic_parser.parse_mds()

    def test_md_devices_marked_as_used(self):
        devices = [
            '/dev/sda',
            '/dev/sdb',
        ]
        spares = [
            '/dev/sdc',
            '/dev/sdd',
        ]
        partition_data = {
            'mds': [{
                'id': 1,
                'name': 'some-raid',
                'level': '1',
                'devices': devices,
                'spares': spares,
            }]
        }
        dynamic_parser = self.get_parser(partition_data)
        dynamic_parser.parse_mds()

        for dev in (devices + spares):
            assert dynamic_parser.is_device_used(dev)

    def check_device_duplication(self, partition_data, duplicated_device):
        dynamic_parser = self.get_parser(partition_data)
        with self.assertRaisesRegexp(
                parser.DuplicatedDeviceError,
                "Device '{0}' is already used".format(duplicated_device)):
            dynamic_parser.parse_mds()

    def test_md_duplicated_devices_between_mds(self):
        duplicated_device = '/dev/sda'
        partition_data = {
            'mds': [
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [
                        duplicated_device,
                    ],
                    'spares': []
                },
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [
                        duplicated_device,
                    ],
                    'spares': []
                }
            ]
        }
        self.check_device_duplication(partition_data, duplicated_device)

    def test_md_duplicated_spares_between_mds(self):
        duplicated_device = '/dev/sda'
        partition_data = {
            'mds': [
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [],
                    'spares': [
                        duplicated_device,
                    ]
                },
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [],
                    'spares': [
                        duplicated_device,
                    ]
                }
            ]
        }
        self.check_device_duplication(partition_data, duplicated_device)

    def test_md_duplicated_device_and_spare_between_mds(self):
        duplicated_device = '/dev/sda'
        partition_data = {
            'mds': [
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [
                        duplicated_device,
                    ],
                    'spares': []
                },
                {
                    'id': 1,
                    'name': 'some-raid',
                    'level': '1',
                    'devices': [],
                    'spares': [
                        duplicated_device,
                    ]
                }
            ]
        }
        self.check_device_duplication(partition_data, duplicated_device)

    def test_md_device_duplicated_in_one_md(self):
        duplicated_device = '/dev/sda'
        partition_data = {
            'mds': [{
                'id': 1,
                'name': 'some-raid',
                'level': '1',
                'devices': [
                    duplicated_device
                ],
                'spares': [
                    duplicated_device
                ],
            }]
        }
        self.check_device_duplication(partition_data, duplicated_device)


class TestParseParted(BaseParsingTestCase):

    def test_parse_full_parted(self):
        partition_data = {
            'parteds': [
                {
                    'id': 1,
                    'name': '/dev/sdb',
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [
                        {
                            'id': 1,
                            'begin': 1,
                            'end': 1000,
                            'partition_type': 'primary',
                        }
                    ]
                },
            ]
        }
        dynamic_parser = self.get_parser(partition_data)
        parteds_adapters = dynamic_parser.parse_parteds()

        assert len(parteds_adapters) == 1
        parteds_adapter = parteds_adapters[0]
        assert isinstance(parteds_adapter, adapters.PartedAdapter)

        parted = parteds_adapter.obj
        assert parted.label == 'gpt'
        assert parted.install_bootloader

        assert len(parted.partitions) == 1
        partition = parted.partitions[0]
        assert isinstance(partition, objects.Partition)
        assert partition.name == '/dev/sdb1'
        assert partition.count == 1
        assert partition.device == '/dev/sdb'
        assert partition.begin == 1
        assert partition.end == 1000
        assert partition.type == 'primary'

    def test_parse_simple_parted(self):
        partition_data = {
            'parteds': [
                {
                    'id': 1,
                    'name': '/dev/sdb',
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [
                        {
                            'id': 1,
                            'size': 1000,
                        }
                    ]
                },
            ]
        }
        dynamic_parser = self.get_parser(partition_data)
        parteds_adapters = dynamic_parser.parse_parteds()

        assert len(parteds_adapters) == 1
        parteds_adapter = parteds_adapters[0]
        assert isinstance(parteds_adapter, adapters.PartedAdapter)

        parted = parteds_adapter.obj
        assert parted.label == 'gpt'
        assert parted.install_bootloader

        assert len(parted.partitions) == 1
        partition = parted.partitions[0]
        assert isinstance(partition, objects.Partition)
        assert partition.name == '/dev/sdb1'
        assert partition.count == 1
        assert partition.device == '/dev/sdb'
        assert partition.begin == 1
        assert partition.end == 1001
        assert partition.type == 'primary'

    def test_error_when_reusing_device(self):
        device = '/dev/sda'

        partition_data = {
            'parteds': [
                {
                    'id': 1,
                    'name': device,
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [
                        {
                            'id': 1,
                            'begin': 1,
                            'end': 100,
                            'partition_type': 'primary',
                        }
                    ]
                },
            ]
        }

        dynamic_parser = self.get_parser(partition_data)
        dynamic_parser.mark_device_as_used(device)

        with self.assertRaisesRegexp(
                parser.DuplicatedDeviceError,
                "Device '{0}' is already used".format(device)):
            dynamic_parser.parse_parteds()

    def test_error_when_duplicated_parteds_ids(self):
        partition_data = {
            'parteds': [
                {
                    'id': 1,
                    'name': '/dev/sda',
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [],
                },
                {
                    'id': 1,
                    'name': '/dev/sdb',
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [],
                },
            ]
        }
        dynamic_parser = self.get_parser(partition_data)
        with self.assertRaisesRegexp(parser.ParserError,
                                     "Duplicated ID 1 for Parted object"):
            dynamic_parser.parse_parteds()

    def test_error_when_duplicated_partitions_ids(self):
        partition_data = {
            'parteds': [
                {
                    'id': 1,
                    'name': '/dev/sdb',
                    'label': 'gpt',
                    'install_bootloader': True,
                    'partitions': [
                        {
                            'id': 3,
                            'begin': 1,
                            'end': 1000,
                            'partition_type': 'primary',
                        },
                        {
                            'id': 3,
                            'begin': 1001,
                            'end': 2000,
                            'partition_type': 'primary',
                        }
                    ]
                },
            ]
        }
        dynamic_parser = self.get_parser(partition_data)
        with self.assertRaisesRegexp(
                parser.ParserError,
                "Duplicated ID 3 for Partition in Parted \(ID 1\) object"):
            dynamic_parser.parse_parteds()
