# Copyright 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest2

from fuel_agent.utils.sizes import SIZES


class TestSizes(unittest2.TestCase):
    test_cases = (
        ('1B', 1),
        ('1 byte', 1),
        ('12bytes', 12),
        ('145', 145),
        ('12kB', 12000),
        ('19.5 kB', 19500),
        ('8000Ki', 8192000),
        ('0.5MB', 500000),
        ('222mega', 222000000),
        ('142342.5435 MB', 142342543500),
        ('15Gi', 16106127360),
        ('5.5 GB', 5500000000),
        ('3 giga', 3000000000),
        ('1 TB', 1000000000000),
        ('15.55 Ti', 17097405811916),
        ('3PB', 3000000000000000),
        ('2pebi', 2251799813685248),
        ('3.14 Pi', 3535325707485839),
        ('1.5EB', 1500000000000000000),
        ('1.456456 EB', 1456456000000000000),
        ('1.4511 Zi', 1713156500823035542398),
        ('2 zetta', 2000000000000000000000),
        ('3.12YB', 3120000000000000000000000),
        ('4YB', 4000000000000000000000000),
        ('123 YiB', 148697875812599388488859648),
    )

    def test_sizes(self):
        for hvalue, bvalue in self.test_cases:
            self.assertEqual(SIZES[hvalue], bvalue)

    def test_sizes_unnecessary_whitespace(self):
        for hvalue, bvalue in self.test_cases:
            hvalue = '   ' + hvalue + '  '
            self.assertEqual(SIZES[hvalue], bvalue)

            ws_hvalue = '  '.join(hvalue.split())
            self.assertEqual(SIZES[ws_hvalue], bvalue)

    def test_not_supported_unit(self):
        test_cases = ('15b', '16mb', '12MEGAGIGA', '42PETA', '12Bi')

        for test in test_cases:
            with self.assertRaisesRegexp(KeyError, 'is not supported'):
                SIZES[test]
