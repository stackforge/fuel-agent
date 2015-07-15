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

from fuel_agent.drivers import dynamic
from fuel_agent import objects


class TestReferences(unittest2.TestCase):

    def test_get_empty_reference(self):
        refs = dynamic.References()
        assert refs['do_not_exists/1'] is None
        assert refs.get('do_not_exists', '1') is None

    def test_add_reference(self):
        refs = dynamic.References()
        refs['some_ref/1'] = 'something'
        assert refs['some_ref/1'] == 'something'
        assert refs.get('some_ref', '1') == 'something'

    def test_add_by_method(self):
        refs = dynamic.References()
        refs.add('some_ref', '1', 'something')
        assert refs['some_ref/1'] == 'something'
        assert refs.get('some_ref', '1') == 'something'

    def test_add_duplicated_reference(self):
        refs = dynamic.References()
        refs.add('some_ref', '1', 'bob_the_builder')
        refs.add('some_ref', '1', 'scoop')
        assert refs['some_ref/1'] == 'scoop'

    def test_add_duplicated_reference_with_stict_mode(self):
        refs = dynamic.References()
        refs.add('some_ref', '1', 'bob_the_builder')
        with self.assertRaisesRegexp(dynamic.DuplicatedReferenceError,
                                     "Reference 'some_ref/1' already exists."):
            refs.add('some_ref', '1', 'scoop', strict=True)

    def test_get_by_type(self):
        refs = dynamic.References()
        refs.add('type', '1', 'A')
        refs.add('type', '2', 'B')
        self.assertItemsEqual(
            refs.get_by_type('type'),
            ['A', 'B']
        )


class TestParseMD(unittest2.TestCase):

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
        parser = dynamic.DynamicPartitionFormat(partition_data, dynamic.Node())
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
        parser = dynamic.DynamicPartitionFormat(partition_data, dynamic.Node())
        with self.assertRaisesRegexp(dynamic.ParserError,
                                     "Duplicated ID 1 for MD object"):
            parser.parse_mds()

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
        parser = dynamic.DynamicPartitionFormat(partition_data, dynamic.Node())
        parser.parse_mds()

        for dev in (devices + spares):
            assert parser.is_device_used(dev)

    def check_device_duplication(self, partition_data, duplicated_device):
        parser = dynamic.DynamicPartitionFormat(partition_data, dynamic.Node())
        with self.assertRaisesRegexp(
                dynamic.DuplicatedDeviceError,
                "Device '{0}' is already used".format(duplicated_device)):
            parser.parse_mds()

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
