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

from fuel_agent.drivers.dynamic import references


class TestReferences(unittest2.TestCase):

    def test_get_empty_reference(self):
        refs = references.References()
        assert refs['do_not_exists/1'] is None
        assert refs.get('do_not_exists', '1') is None

    def test_add_reference(self):
        refs = references.References()
        refs['some_ref/1'] = 'something'
        assert refs['some_ref/1'] == 'something'
        assert refs.get('some_ref', '1') == 'something'

    def test_add_by_method(self):
        refs = references.References()
        refs.add('some_ref', '1', 'something')
        assert refs['some_ref/1'] == 'something'
        assert refs.get('some_ref', '1') == 'something'

    def test_add_duplicated_reference(self):
        refs = references.References()
        refs.add('some_ref', '1', 'bob_the_builder')
        refs.add('some_ref', '1', 'scoop')
        assert refs['some_ref/1'] == 'scoop'

    def test_add_duplicated_reference_with_stict_mode(self):
        refs = references.References()
        refs.add('some_ref', '1', 'bob_the_builder')
        with self.assertRaisesRegexp(references.DuplicatedReferenceError,
                                     "Reference 'some_ref/1' already exists."):
            refs.add('some_ref', '1', 'scoop', strict=True)

    def test_get_by_type(self):
        refs = references.References()
        refs.add('type', '1', 'A')
        refs.add('type', '2', 'B')
        self.assertItemsEqual(
            refs.get_by_type('type'),
            ['A', 'B']
        )
