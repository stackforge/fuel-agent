# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
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
import mock

from fuel_bootstrap.tests import base


class TestActivateCommand(base.BaseTest):

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.activate',
                return_value='fake_uuid')
    def test_parser(self, mock_activate):
        self.app.run(['activate', 'fake_uuid'])
        mock_activate.assert_called_once_with('fake_uuid')
        self.assertEqual("Bootstrap image {0} has been activated.\n"
                         .format("fake_uuid"), self.app.stdout.getvalue())
