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

import copy

import unittest2

from fuel_agent import errors
from fuel_agent.tests import base
from fuel_agent.validators import volumes as validators


class TestPartitionSchemaValidation(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALID_PARTITION_DATA = base.load_fixture(
            'human_readable_format.json')

    def _get_partition_data(self):
        return copy.deepcopy(self.VALID_PARTITION_DATA)

    def setUp(self):
        self.validator = validators.HumanReadableSchemeValidator(
            self.VALID_PARTITION_DATA)

    def test_validation_success(self):
        assert self.validator.validate(self.VALID_PARTITION_DATA) is None

    def test_vg_pvs_ids_fail(self):
        invalid = self._get_partition_data()
        invalid['vgs'][0]['pvs'] = [40, 50]

        with self.assertRaises(errors.WrongPartitionSchemeError):
            self.validator.validate(invalid)

    def test_lv_vg_id_fail(self):
        invalid = self._get_partition_data()
        invalid['lvs'][0]['vgname'] = 'thereisnospoon'

        with self.assertRaises(errors.WrongPartitionSchemeError):
            self.validator.validate(invalid)

    def test_md_invalid_device_fail(self):
        invalid = self._get_partition_data()
        invalid['mds'][0]['devices'][0] = 'gibberish'

        with self.assertRaises(errors.WrongPartitionSchemeError):
            self.validator.validate(invalid)

    def test_non_existent_device_by_metadata_fail(self):
        invalid = self._get_partition_data()
        invalid['fss'][0]['device'] = '@lv/30'

        with self.assertRaises(errors.WrongPartitionSchemeError):
            self.validator.validate(invalid)

    def test_vgs_overlap_fail(self):
        invalid = self._get_partition_data()
        invalid['vgs'][0]['pvs'] = [1, 2, 3]
        invalid['vgs'][1]['pvs'] = [2, 3]

        with self.assertRaises(errors.WrongPartitionSchemeError):
            self.validator.validate(invalid)
