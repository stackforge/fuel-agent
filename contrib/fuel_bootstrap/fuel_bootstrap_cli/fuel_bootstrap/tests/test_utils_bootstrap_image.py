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

import fuel_agent
import mock
import unittest2

import fuel_bootstrap
from fuel_bootstrap import consts
from fuel_bootstrap import errors
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

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.tempfile')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.extract_to_dir')
    def test_import_exists_image(self,
                                 extract_mock,
                                 tempfile_mock,
                                 os_mock,
                                 yaml_mock,
                                 open_mock):
        arch_path = '/test/arch_path'
        data = {'uuid': '/test/42'}
        image_uuid = data['uuid']

        yaml_mock.safe_load.return_value = data
        os_mock.path.exists.return_value = True

        error_msg = ("Image [{0}] already exists."
                     .format(image_uuid))
        with self.assertRaises(errors.ImageAlreadyExists, msg=error_msg):
            bs_image.import_image(arch_path)

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.tempfile')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.extract_to_dir')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.shutil')
    def test_import_image(self,
                          shutil_mock,
                          extract_mock,
                          tempfile_mock,
                          os_mock,
                          yaml_mock,
                          open_mock):
        extract_mock = '/tmp/test'
        arch_path = '/test/arch_path'
        data = {'uuid': '/test/42'}
        expected_image_uuid = data['uuid']
        dir_path = expected_image_uuid

        tempfile_mock.mkdtemp.return_value = extract_mock
        yaml_mock.safe_load.return_value = data
        os_mock.path.exists.return_value = False

        image_uuid = bs_image.import_image(arch_path)
        self.assertEqual(expected_image_uuid, image_uuid)
        shutil_mock.move.assert_called_once_with(extract_mock, dir_path)

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.tarfile')
    def test_extract_to_dir(self, tarfile_mock):
        arch_path = '/test/arch/path'
        extract_path = '/test/extract/path'
        bs_image.extract_to_dir(arch_path, extract_path)
        tarfile_mock.open.assert_called_once_with(arch_path, 'r')
        tarfile_mock.open().extractall.assert_called_once_with(extract_path)

    @mock.patch.object(fuel_bootstrap.utils.data, 'BootstrapDataBuilder')
    @mock.patch.object(fuel_agent.manager, 'Manager')
    def test_make_bootstrap(self, manager_mock, bdb_mock):
        data = {}
        boot_data = {'bootstrap': {'uuid': '42'},
                     'output': '/image/path'}
        bdb_mock(data).build.return_value = boot_data

        self.assertEqual(('42', '/image/path'), bs_image.make_bootstrap(data))
        manager_mock(boot_data).do_mkbootstrap.assert_called()

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    def test_update_astute_yaml_key_error(self, yaml_mock, open_mock):
        yaml_mock.safe_load.return_value = {}
        with self.assertRaises(KeyError):
            bs_image._update_astute_yaml()

    @mock.patch('fuel_bootstrap.utils.bootstrap_image.open',
                create=True, new_callable=mock.mock_open)
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.yaml')
    def test_update_astute_yaml_type_error(self, yaml_mock, open_mock):
        yaml_mock.safe_load.return_value = []
        with self.assertRaises(TypeError):
            bs_image._update_astute_yaml()

    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_run_puppet_no_manifest(self, execute_mock):
        bs_image._run_puppet()
        execute_mock.assert_called_once()

    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_run_puppet_cobbler_manifest(self, execute_mock):
        bs_image._run_puppet(consts.COBBLER_MANIFEST)
        execute_mock.assert_called_once()

    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_run_puppet_astute_manifest(self, execute_mock):
        bs_image._run_puppet(consts.ASTUTE_MANIFEST)
        execute_mock.assert_called_once()

    def test_activate_flavor_not_in_distros(self):
        flavor = 'not_ubuntu'
        error_msg = ('Wrong cobbler profile passed:%s \n possible profiles:',
                     flavor, consts.DISTROS.keys())
        with self.assertRaises(errors.WrongCobblerProfile, msg=error_msg):
            bs_image._activate_flavor(flavor)

    @mock.patch.object(bs_image, '_update_astute_yaml')
    @mock.patch.object(bs_image, '_run_puppet')
    @mock.patch.object(fuel_agent.utils.utils, 'execute')
    def test_activate_flavor(self,
                             execute_mock,
                             run_puppet_mock,
                             update_astute_yaml_mock):
        flavor = 'ubuntu'
        bs_image._activate_flavor(flavor)
        update_astute_yaml_mock.assert_called_once_with(
            consts.DISTROS[flavor]['astute_flavor'])
        run_puppet_mock.assert_any_call(consts.COBBLER_MANIFEST)
        run_puppet_mock.assert_any_call(consts.ASTUTE_MANIFEST)
        execute_mock.assert_called_once()

    @mock.patch.object(bs_image, 'CONF')
    @mock.patch.object(bs_image, '_activate_flavor')
    @mock.patch.object(fuel_bootstrap.utils.notifier, 'notify_webui')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test__activate(self,
                       os_mock,
                       notify_mock,
                       activate_flavor_mock,
                       conf_mock):
        image_uuid = '/test/test_image_uuid'
        os_mock.lexists.return_value = False
        self.assertEqual(image_uuid, bs_image._activate(image_uuid))
        activate_flavor_mock.assert_called_once_with('ubuntu')
        notify_mock.assert_called_once()

    @mock.patch.object(bs_image, 'CONF')
    @mock.patch.object(bs_image, '_activate_flavor')
    @mock.patch.object(fuel_bootstrap.utils.notifier, 'notify_webui')
    @mock.patch('fuel_bootstrap.utils.bootstrap_image.os')
    def test__activate_symlink_deleted(self,
                                       os_mock,
                                       notify_mock,
                                       activate_flavor_mock,
                                       conf_mock):
        image_uuid = '/test/test_image_uuid'
        os_mock.lexists.return_value = True
        self.assertEqual(image_uuid, bs_image._activate(image_uuid))
        activate_flavor_mock.assert_called_once_with('ubuntu')
        notify_mock.assert_called_once()

    @mock.patch.object(bs_image, 'parse')
    @mock.patch.object(bs_image, '_activate')
    def test_activate(self, activate_mock, parse_mock):
        image_uuid = '/test/test_image_uuid'
        activate_mock.return_value = image_uuid
        self.assertEqual(image_uuid, bs_image.activate(image_uuid))
