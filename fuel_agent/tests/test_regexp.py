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

from fuel_agent import consts


class TestRegexp(unittest2.TestCase):
    path_positive = ('/dev/sda, /dev/sd1', '/dev/sdb')

    def matches(self, regexp, cases):
        for case in cases:
            self.assertRegexpMatches(case, regexp)

    def not_matches(self, regexp, cases):
        for case in cases:
            self.assertNotRegexpMatches(case, regexp)

    def test_path_regexp(self):
        self.matches(consts.PATH_REGEXP, self.path_positive)

    def test_path_regexp_negative(self):
        test_cases = ('dev/sda', 'device')
        self.not_matches(consts.PATH_REGEXP, test_cases)

    def test_device_regexp(self):
        test_cases = ('@lvs/1', '@mds/23', '@parteds/1/2') + self.path_positive
        self.matches(consts.DEVICE_REGEXP, test_cases)

    def test_device_not_matches(self):
        test_cases = ('lvs/2', '@LVS/1', '@parteds', 'mds')
        self.not_matches(consts.DEVICE_REGEXP, test_cases)

    def test_human_readable_regexp(self):
        test_cases = ('1B', '1 byte', '12bytes', '145', '12kB', '19.5 kB',
                      '8000Ki', '0.5MB', '222mega', '142342.5435 MB', '15Gi',
                      '5.5 GB', '3 giga', '1 TB', '15,55 Ti', '3PB', '2pebi',
                      '3.14 Pi', '1,5EB', '1,456456 EB', '1.4511 Zi',
                      '2 zetta', '3.12YB', '4YB', '123 YiB')
        self.matches(consts.HUMAN_READABLE_SIZE_REGEXP, test_cases)

    def test_human_readable_regexp_negative(self):
        test_cases = ('124 TT', 'KiB', '123 KK', '234ZZ', '12kb')
        self.not_matches(consts.HUMAN_READABLE_SIZE_REGEXP, test_cases)
