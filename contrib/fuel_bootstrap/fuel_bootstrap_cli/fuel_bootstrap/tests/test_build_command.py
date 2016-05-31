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

PARSED_ARGS = {'extend_kopts': None,
               'no_compress': False,
               'output_dir': None,
               'image_build_dir': None,
               'post_script_file': None,
               'root_ssh_authorized_file': None,
               'activate': False,
               'ubuntu_release': None,
               'root_password': None,
               'no_default_direct_repo_addr': False,
               'https_proxy': None,
               'http_proxy': None,
               'direct_repo_addr': None,
               'label': None,
               'repos': None,
               'kernel_flavor': None,
               'certs': None,
               'extra_dirs': None,
               'no_default_packages': False,
               'no_default_extra_dirs': False,
               'packages': None}


class TestBuildCommand(base.BaseTest):
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.make_bootstrap',
                return_value=('fake_uuid', 'fake_path'))
    def test_parser(self, mock_make_bootstrap):
        self.app.run(['build'])
        mock_make_bootstrap.assert_called_once_with(PARSED_ARGS)
        self.assertEqual("Bootstrap image {0} has been built: {1}\n"
                         .format("fake_uuid", 'fake_path'),
                         self.app.stdout.getvalue())

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.activate',
                return_value=('fake_uuid', 'fake_path'))
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.import_image',
                return_value='fake_uuid')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.make_bootstrap',
                return_value=('fake_uuid', 'fake_path'))
    def test_parser_activate(self, mock_make_bootstrap,
                             mock_import, mock_activate):
        self.app.run(['build', '--activate'])
        PARSED_ARGS['activate'] = True
        mock_make_bootstrap.assert_called_once_with(PARSED_ARGS)
        mock_import.assert_called_once_with('fake_path')
        mock_activate.assert_called_once_with('fake_uuid')
        self.assertEqual("Bootstrap image {0} has been built: {1}\n"
                         "Bootstrap image {0} has been activated.\n"
                         .format("fake_uuid", 'fake_path'),
                         self.app.stdout.getvalue())
