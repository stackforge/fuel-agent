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


class TestPartitionAdapter(unittest2.TestCase):

    def test_pass_begin_and_end(self):
        adapter = adapters.PartitionAdapter({
            'id': 1,
            'begin': 1,
            'end': 123,
        })

        assert adapter.id == 1
        assert adapter.begin == 1
        assert adapter.end == 123
        assert adapter.size == 122

        assert adapter.min_size == 122
        assert adapter.best_size == 122
        assert adapter.max_size == 122

        assert adapter.parsed_data == {
            'begin': 1,
            'end': 123,
        }

    def test_begin_and_end_has_priority(self):

        adapter = adapters.PartitionAdapter({
            'id': 1,
            'begin': 1,
            'end': 123,
            'size': 997,
        })

        assert adapter.id == 1
        assert adapter.begin == 1
        assert adapter.end == 123
        assert adapter.size == 122

        assert adapter.min_size == 122
        assert adapter.best_size == 122
        assert adapter.max_size == 122

        assert adapter.parsed_data == {
            'begin': 1,
            'end': 123,
        }

    def test_pass_exact_size(self):
        adapter = adapters.PartitionAdapter({
            'id': 1,
            'size': 456,
        })

        assert adapter.id == 1
        assert adapter.begin is None
        assert adapter.end is None
        assert adapter.size == 456

        assert adapter.min_size == 456
        assert adapter.best_size == 456
        assert adapter.max_size == 456

        assert adapter.parsed_data == {
            'size': 456,
        }

    def test_pass_complex_size(self):
        adapter = adapters.PartitionAdapter({
            'id': 1,
            'size': {
                'min': 128,
                'best': 256,
                'max': 512,
            }
        })

        assert adapter.id == 1
        assert adapter.begin is None
        assert adapter.end is None
        assert adapter.size == 128

        assert adapter.min_size == 128
        assert adapter.best_size == 256
        assert adapter.max_size == 512

        assert adapter.parsed_data == {
            'size': 128,
        }


class TestPartedAdapter(object):

    def test_parse_partitons(self):
        adapter = adapters.PartedAdapter({
            'id': 1,
            'name': '/dev/sda',
            'label': 'gpt',
            'partitions': [
                {
                    'id': 1,
                    'size': 456,
                },
                {
                    'id': 2,
                    'size': 789,
                }
            ]
        })

        partitions = list(adapter.partitions)
        assert len(partitions) == 2
        for partition in partitions:
            assert isinstance(partition, adapters.PartitionAdapter)
