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

import os
import tempfile

import fuel_agent
import mock
import unittest2

import fuel_bootstrap
from fuel_bootstrap import errors
from fuel_bootstrap.objects import master_node_settings
from fuel_bootstrap.utils import bootstrap_image as bs_image


class BootstrapImageTestCase(unittest2.TestCase):

    def setUp(self):
        super(BootstrapImageTestCase, self).setUp()

    @mock.patch.object(bs_image, 'parse')
    @mock.patch.object(bs_image, 'CONF')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_get_all(self, os_mock, conf_mock, parse_mock):
        os_mock.listdir.return_value = ["dir1", "file", "dir2"]
        os_mock.path.isdir.side_effect = [True, False, True]

        data = [{'name': 'fake_image1'}, {'name': 'fake_image2'}]
        parse_mock.side_effect = data
        self.assertEqual(data, bs_image.get_all())
        self.assertEqual(2, parse_mock.call_count)
        parse_mock.assert_has_calls([mock.call('dir1'), mock.call('dir2')])

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_link(self, os_mock):
        os_mock.path.islink.return_value = True
        image_uuid = '/test'
        error_msg = "There are no such image [{0}].".format(image_uuid)
        with self.assertRaises(errors.IncorrectImage, msg=error_msg):
            bs_image.parse(image_uuid)

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_not_dir(self, os_mock):
        os_mock.path.islink.return_value = False
        os_mock.path.isdir.return_value = False
        image_uuid = '/test'
        error_msg = "There are no such image [{0}].".format(image_uuid)
        with self.assertRaises(errors.IncorrectImage, msg=error_msg):
            bs_image.parse(image_uuid)

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_no_metadata(self, os_mock):
        os_mock.path.islink.return_value = False
        os_mock.path.isdir.return_value = True
        os_mock.path.join.return_value = 'fake_metadata'
        os_mock.path.exists.return_value = False
        image_uuid = '/test'
        error_msg = ("Image [{0}] doesn't contain metadata file."
                     .format(image_uuid))
        with self.assertRaises(errors.IncorrectImage, msg=error_msg):
            bs_image.parse(image_uuid)

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_wrong_dir_name(self, os_mock, yaml_mock, open_mock):
        os_mock.path.islink.return_value = False
        os_mock.path.isdir.return_value = True
        os_mock.path.join.return_value = 'fake_metadata'
        os_mock.path.exists.return_value = True

        data = {'uuid': '42'}
        yaml_mock.safe_load.return_value = data
        image_uuid = '/test'
        error_msg = ("UUID from metadata file [{0}] doesn't equal"
                     " directory name [{1}]".format('42', image_uuid))
        with self.assertRaises(errors.IncorrectImage, msg=error_msg):
            bs_image.parse(image_uuid)

    @mock.patch.object(bs_image, 'is_active')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_correct_image(self, os_mock, yaml_mock, open_mock,
                                 active_mock):
        os_mock.path.islink.return_value = False
        os_mock.path.isdir.return_value = True
        os_mock.path.join.return_value = 'fake_metadata'
        os_mock.path.exists.return_value = True
        os_mock.path.basename.return_value = '42'
        active_mock.return_value = False

        expected_data = {'uuid': '42'}
        yaml_mock.safe_load.return_value = expected_data
        expected_data.update({'label': '', 'active': ''})

        image_uuid = '/test'
        data = bs_image.parse(image_uuid)

        self.assertEqual(expected_data, data)

    @mock.patch.object(bs_image, 'is_active')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test_parse_active_image(self, os_mock, yaml_mock, open_mock,
                                active_mock):
        os_mock.path.islink.return_value = False
        os_mock.path.isdir.return_value = True
        os_mock.path.join.return_value = 'fake_metadata'
        os_mock.path.exists.return_value = True
        os_mock.path.basename.return_value = '42'
        active_mock.return_value = True

        expected_data = {'uuid': '42', 'label': ''}
        yaml_mock.safe_load.return_value = expected_data
        expected_data.update({'label': '', 'active': ''})

        image_uuid = '/test'
        data = bs_image.parse(image_uuid)

        self.assertEqual(expected_data, data)

    @mock.patch.object(bs_image, 'parse')
    def test_delete_active_image(self, parse_mock):
        parse_mock.return_value = {'status': bs_image.ACTIVE}
        image_uuid = '/test'
        error_msg = ("Image [{0}] is active and can't be deleted."
                     .format(image_uuid))

        with self.assertRaises(errors.ActiveImageException, msg=error_msg):
            bs_image.delete(image_uuid)

    @mock.patch.object(bs_image, 'parse')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.shutil')
    def test_delete(self, shutil_mock, parse_mock):
        image_uuid = '/test'
        self.assertEqual(image_uuid, bs_image.delete(image_uuid))
        shutil_mock.rmtree.assert_called_once_with(image_uuid)

    @mock.patch.object(os.path, 'realpath')
    def test_is_active(self, realpath_mock):
        image_uuid = '/test/image_uuid'
        realpath_mock.return_value = '/test/image_uuid'
        self.assertTrue(bs_image.is_active(image_uuid))

    @mock.patch.object(bs_image, 'CONF')
    def test_full_path_not_full(self, conf_mock):
        image_uuid = 'test_image_uuid'
        conf_mock.bootstrap_images_dir = '/test/image/dir/'
        result = bs_image.full_path(image_uuid)
        self.assertEqual('/test/image/dir/test_image_uuid', result)

    @mock.patch.object(bs_image, 'CONF')
    def test_full_path_full(self, conf_mock):
        image_uuid = '/test/test_image_uuid'
        conf_mock.bootstrap_images_dir = '/test/image/dir/'
        result = bs_image.full_path(image_uuid)
        self.assertEqual('/test/test_image_uuid', result)

    def test_import_image(self):
        pass

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.tarfile')
    def test_extract_to_dir(self, tarfile_mock):
        arch_path = '/test/arch/path'
        extract_path = '/test/extract/path'
        bs_image.extract_to_dir(arch_path, extract_path)
        tarfile_mock.open.assert_called_once_with(arch_path, 'r')
        tarfile_mock.open().extractall.assert_called_once_with(extract_path)

    @mock.patch.object(fuel_bootstrap.utils.data, 'BootstrapDataBuilder')
    @mock.patch.object(tempfile, 'NamedTemporaryFile')
    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_make_bootstrap(self, execute_mock, ntf_mock, bdb_mock):
        bdb_mock().build.return_value = {'bootstrap': {'uuid': '42'},
                                         'output': '/image/path'}
        file_name = 'temp_name'
        ntf_mock().__enter__().name = file_name
        self.assertEqual(('42', '/image/path'), bs_image.make_bootstrap())
        opts = ['fa_mkbootstrap', '--nouse-syslog', '--data_driver',
                'bootstrap_build_image', '--nodebug', '-v',
                '--input_data_file', 'temp_name']
        execute_mock.assert_called_once_with(*opts)

    @mock.patch.object(bs_image, 'parse')
    @mock.patch.object(bs_image, 'CONF')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_activate_ubuntu(self, execute_mock, os_mock, conf_mock,
                             parse_mock):
        image_uuid = '/test'
        symlink = '/fake/symlink'
        conf_mock.active_bootstrap_symlink = symlink
        self.assertEqual(image_uuid, bs_image.activate(image_uuid))
        os_mock.unlink.assert_called_once_with(symlink)
        parse_mock.assert_called_once_with(image_uuid)
        os_mock.symlink.assert_called_once_with(image_uuid, symlink)
        execute_mock.assert_called_once_with(
            'fuel-bootstrap-image-set', 'ubuntu')

    @mock.patch.object(bs_image, 'CONF')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_activate_centos(self, execute_mock, os_mock, conf_mock):
        image_uuid = 'centos'
        symlink = '/fake/symlink'
        conf_mock.active_bootstrap_symlink = symlink
        self.assertEqual(image_uuid, bs_image.activate(image_uuid))
        os_mock.unlink.assert_called_once_with(symlink)
        self.assertEqual(0, os_mock.symlink.call_count)
        execute_mock.assert_called_once_with(
            'fuel-bootstrap-image-set', 'centos')

    @mock.patch.object(bs_image, 'make_bootstrap')
    def test_call_wrapped_method_make_bootstrap(self, mb_mock):
        data = {'test': 'test'}
        bs_image.call_wrapped_method('build', False, data=data)
        mb_mock.assert_called_once_with(data=data)

    @mock.patch.object(bs_image, 'activate')
    def test_call_wrapped_method_activate(self, activate_mock):
        image_uuid = 'test_image_uuid'
        bs_image.call_wrapped_method('activate', False, image_uuid=image_uuid)
        activate_mock.assert_called_once_with(image_uuid=image_uuid)

    @mock.patch.object(bs_image, 'activate')
    @mock.patch.object(bs_image, 'notify_webui_about_results')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.consts')
    def test_call_wrapped_method_activate_with_notification(
            self, consts_mock, notify_mock, activate_mock):
        exception_msg = 'fake_exception'
        error_msg = 'fake_error_msg'
        activate_mock.side_effect = errors.IncorrectImage(exception_msg)
        consts_mock.ERROR_MSG = error_msg

        with self.assertRaises(errors.IncorrectImage, msg=exception_msg):
            bs_image.call_wrapped_method('activate', True)

        notify_mock.assert_called_once_with(True, error_msg)

    @mock.patch.object(master_node_settings, 'MasterNodeSettings')
    def test_notify_webui_about_results_true(self, mns_mock):
        mn_settings_mock = mns_mock()
        mn_settings_mock.get.return_value = {'settings': {}}
        bs_image.notify_webui_about_results(True, 'test_message')
        mn_settings_mock.update.assert_called_once_with({
            'settings': {
                'bootstrap': {
                    'error': {
                        'value': 'test_message'
                    }
                }
            }
        })

    @mock.patch.object(master_node_settings, 'MasterNodeSettings')
    def test_notify_webut_about_results_false(self, mns_mock):
        mn_settings_mock = mns_mock()
        mn_settings_mock.get.return_value = {'settings': {}}
        bs_image.notify_webui_about_results(False, 'test_message')
        mn_settings_mock.update.assert_called_once_with({
            'settings': {
                'bootstrap': {
                    'error': {
                        'value': ''
                    }
                }
            }
        })
