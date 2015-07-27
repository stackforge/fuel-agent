# Copyright 2011 Justin Santa Barbara
# Copyright 2012 Hewlett-Packard Development Company, L.P.
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

import socket

import mock
from oslo.config import cfg
import requests
import stevedore
import unittest2
import urllib3

from fuel_agent import errors
from fuel_agent.utils import utils


CONF = cfg.CONF


class ExecuteTestCase(unittest2.TestCase):
    """This class is partly based on the same class in openstack/ironic."""

    def setUp(self):
        super(ExecuteTestCase, self).setUp()
        fake_driver = stevedore.extension.Extension('fake_driver', None, None,
                                                    mock.MagicMock)
        self.drv_manager = stevedore.driver.DriverManager.make_test_instance(
            fake_driver)

    def test_parse_unit(self):
        self.assertEqual(utils.parse_unit('1.00m', 'm', ceil=True), 1)
        self.assertEqual(utils.parse_unit('1.00m', 'm', ceil=False), 1)
        self.assertEqual(utils.parse_unit('1.49m', 'm', ceil=True), 2)
        self.assertEqual(utils.parse_unit('1.49m', 'm', ceil=False), 1)
        self.assertEqual(utils.parse_unit('1.51m', 'm', ceil=True), 2)
        self.assertEqual(utils.parse_unit('1.51m', 'm', ceil=False), 1)
        self.assertRaises(ValueError, utils.parse_unit, '1.00m', 'MiB')
        self.assertRaises(ValueError, utils.parse_unit, '', 'MiB')

    def test_B2MiB(self):
        self.assertEqual(utils.B2MiB(1048575, ceil=False), 0)
        self.assertEqual(utils.B2MiB(1048576, ceil=False), 1)
        self.assertEqual(utils.B2MiB(1048575, ceil=True), 1)
        self.assertEqual(utils.B2MiB(1048576, ceil=True), 1)
        self.assertEqual(utils.B2MiB(1048577, ceil=True), 2)

    def test_check_exit_code_boolean(self):
        utils.execute('/usr/bin/env', 'false', check_exit_code=False)
        self.assertRaises(errors.ProcessExecutionError,
                          utils.execute,
                          '/usr/bin/env', 'false', check_exit_code=True)

    @mock.patch('fuel_agent.utils.utils.time.sleep')
    @mock.patch('fuel_agent.utils.utils.subprocess.Popen')
    def test_execute_ok_on_third_attempts(self, mock_popen, mock_sleep):
        process = mock.Mock()
        mock_popen.side_effect = [OSError, ValueError, process]
        process.communicate.return_value = (None, None)
        process.returncode = 0
        utils.execute('/usr/bin/env', 'false', attempts=3)
        self.assertEqual(2 * [mock.call(CONF.execute_retry_delay)],
                         mock_sleep.call_args_list)

    @mock.patch('fuel_agent.utils.utils.time.sleep')
    @mock.patch('fuel_agent.utils.utils.subprocess.Popen')
    def test_execute_failed(self, mock_popen, mock_sleep):
        mock_popen.side_effect = OSError
        self.assertRaises(errors.ProcessExecutionError, utils.execute,
                          '/usr/bin/env', 'false', attempts=2)
        self.assertEqual(1 * [mock.call(CONF.execute_retry_delay)],
                         mock_sleep.call_args_list)

    @mock.patch('stevedore.driver.DriverManager')
    def test_get_driver(self, mock_drv_manager):
        mock_drv_manager.return_value = self.drv_manager
        self.assertEqual(mock.MagicMock.__name__,
                         utils.get_driver('fake_driver').__name__)

    @mock.patch('jinja2.Environment')
    @mock.patch('jinja2.FileSystemLoader')
    @mock.patch('six.moves.builtins.open')
    def test_render_and_save_fail(self, mock_open, mock_j_lo, mock_j_env):
        mock_open.side_effect = Exception('foo')
        self.assertRaises(errors.TemplateWriteError, utils.render_and_save,
                          'fake_dir', 'fake_tmpl_name', 'fake_data',
                          'fake_file_name')

    @mock.patch('jinja2.Environment')
    @mock.patch('jinja2.FileSystemLoader')
    @mock.patch('six.moves.builtins.open')
    def test_render_and_save_ok(self, mock_open, mock_j_lo, mock_j_env):
        mock_render = mock.Mock()
        mock_render.render.return_value = 'fake_data'
        mock_j_env.get_template.return_value = mock_render
        utils.render_and_save('fake_dir', 'fake_tmpl_name', 'fake_data',
                              'fake_file_name')
        mock_open.assert_called_once_with('fake_file_name', 'w')

    def test_calculate_md5_ok(self):
        # calculated by 'printf %10000s | md5sum'
        with mock.patch('six.moves.builtins.open',
                        mock.mock_open(read_data=' ' * 10000), create=True):
            self.assertEqual('f38898bb69bb02bccb9594dfe471c5c0',
                             utils.calculate_md5('fake', 10000))
            self.assertEqual('6934d9d33cd2d0c005994e7d96d2e0d9',
                             utils.calculate_md5('fake', 1000))
            self.assertEqual('1e68934346ee57858834a205017af8b7',
                             utils.calculate_md5('fake', 100))
            self.assertEqual('41b394758330c83757856aa482c79977',
                             utils.calculate_md5('fake', 10))
            self.assertEqual('7215ee9c7d9dc229d2921a40e899ec5f',
                             utils.calculate_md5('fake', 1))
            self.assertEqual('d41d8cd98f00b204e9800998ecf8427e',
                             utils.calculate_md5('fake', 0))

    @mock.patch.object(requests, 'get')
    def test_init_http_request_ok(self, mock_req):
        utils.init_http_request('fake_url')
        mock_req.assert_called_once_with(
            'fake_url', stream=True, timeout=CONF.http_request_timeout,
            headers={'Range': 'bytes=0-'})

    @mock.patch('time.sleep')
    @mock.patch.object(requests, 'get')
    def test_init_http_request_non_critical_errors(self, mock_req, mock_s):
        mock_ok = mock.Mock()
        mock_req.side_effect = [urllib3.exceptions.DecodeError(),
                                urllib3.exceptions.ProxyError(),
                                requests.exceptions.ConnectionError(),
                                requests.exceptions.Timeout(),
                                requests.exceptions.TooManyRedirects(),
                                socket.timeout(),
                                mock_ok]
        req_obj = utils.init_http_request('fake_url')
        self.assertEqual(mock_ok, req_obj)

    @mock.patch.object(requests, 'get')
    def test_init_http_request_wrong_http_status(self, mock_req):
        mock_fail = mock.Mock()
        mock_fail.raise_for_status.side_effect = KeyError()
        mock_req.return_value = mock_fail
        self.assertRaises(KeyError, utils.init_http_request, 'fake_url')

    @mock.patch('time.sleep')
    @mock.patch.object(requests, 'get')
    def test_init_http_request_max_retries_exceeded(self, mock_req, mock_s):
        mock_req.side_effect = requests.exceptions.ConnectionError()
        self.assertRaises(errors.HttpUrlConnectionError,
                          utils.init_http_request, 'fake_url')

    @mock.patch('fuel_agent.utils.utils.os.makedirs')
    @mock.patch('fuel_agent.utils.utils.os.path.isdir', return_value=False)
    def test_makedirs_if_not_exists(self, mock_isdir, mock_makedirs):
        utils.makedirs_if_not_exists('/fake/path')
        mock_isdir.assert_called_once_with('/fake/path')
        mock_makedirs.assert_called_once_with('/fake/path', mode=0o755)

    @mock.patch('fuel_agent.utils.utils.os.makedirs')
    @mock.patch('fuel_agent.utils.utils.os.path.isdir', return_value=False)
    def test_makedirs_if_not_exists_mode_given(
            self, mock_isdir, mock_makedirs):
        utils.makedirs_if_not_exists('/fake/path', mode=0o000)
        mock_isdir.assert_called_once_with('/fake/path')
        mock_makedirs.assert_called_once_with('/fake/path', mode=0o000)

    @mock.patch('fuel_agent.utils.utils.os.makedirs')
    @mock.patch('fuel_agent.utils.utils.os.path.isdir', return_value=True)
    def test_makedirs_if_not_exists_already_exists(
            self, mock_isdir, mock_makedirs):
        utils.makedirs_if_not_exists('/fake/path')
        mock_isdir.assert_called_once_with('/fake/path')
        self.assertEqual(mock_makedirs.mock_calls, [])

    @mock.patch('fuel_agent.utils.utils.os.listdir')
    def test_guess_filename(self, mock_oslistdir):
        mock_oslistdir.return_value = ['file1', 'file2', 'file3']
        filename = utils.guess_filename('/some/path', '^file2.*')
        self.assertEqual(filename, 'file2')
        mock_oslistdir.assert_called_once_with('/some/path')

    @mock.patch('fuel_agent.utils.utils.os.listdir')
    def test_guess_filename_not_found(self, mock_oslistdir):
        mock_oslistdir.return_value = ['file1', 'file2', 'file3']
        filename = utils.guess_filename('/some/path', '^file4.*')
        self.assertIsNone(filename)
        mock_oslistdir.assert_called_once_with('/some/path')

    @mock.patch('fuel_agent.utils.utils.os.listdir')
    def test_guess_filename_not_exact_match(self, mock_oslistdir):
        mock_oslistdir.return_value = ['file1', 'file2', 'file3']
        filename = utils.guess_filename('/some/path', '^file.*')
        # by default files are sorted in backward direction
        self.assertEqual(filename, 'file3')
        mock_oslistdir.assert_called_once_with('/some/path')

    @mock.patch('fuel_agent.utils.utils.os.listdir')
    def test_guess_filename_not_exact_match_forward_sort(self, mock_oslistdir):
        mock_oslistdir.return_value = ['file1', 'file2', 'file3']
        filename = utils.guess_filename('/some/path', '^file.*', reverse=False)
        # by default files are sorted in backward direction
        self.assertEqual(filename, 'file1')
        mock_oslistdir.assert_called_once_with('/some/path')

    @mock.patch.object(utils, 'open', create=True, new_callable=mock.mock_open)
    @mock.patch.object(utils.os.path, 'basename')
    @mock.patch.object(utils.os.path, 'exists')
    @mock.patch.object(utils.os.path, 'isdir')
    @mock.patch.object(utils.os.path, 'join')
    @mock.patch.object(utils.os, 'listdir')
    @mock.patch.object(utils.os, 'symlink')
    @mock.patch.object(utils.os, 'rename')
    @mock.patch.object(utils, 'execute')
    def test_blacklist_udev_rules(self, mock_execute, mock_os_rename,
                                  mock_os_symlink, mock_os_listdir,
                                  mock_os_join, mock_os_isdir, mock_os_exists,
                                  mock_os_basename, mock_open):
        def _fake_join(path1, path2):
            return '{0}/{1}'.format(path1, path2)

        mock_os_join.side_effect = _fake_join
        mock_os_basename.return_value = 'fake_basename'
        mock_os_listdir.return_value = [
            'not_a_rule', 'fake.rules', 'fake_err.rules', 'dir']
        mock_os_rename.side_effect = [None, OSError]
        mock_os_isdir.side_effect = [False] * 3 + [True]
        mock_os_exists.return_value = True
        utils.blacklist_udev_rules()
        mock_open.assert_called_once_with('/etc/udev/rules.d/fake_basename',
                                          'w')
        file_handler = mock_open.return_value.__enter__.return_value
        file_handler.write.assert_called_once_with('#\n')
        mock_os_basename.assert_called_once_with('empty_rule')
        self.assertEqual([mock.call('/etc/udev/rules.d/not_a_rule'),
                          mock.call('/etc/udev/rules.d/fake.rules'),
                          mock.call('/etc/udev/rules.d/fake_err.rules'),
                          mock.call('/etc/udev/rules.d/dir')],
                         mock_os_isdir.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d/fake.rules'),
                          mock.call('/etc/udev/rules.d/fake_err.rules')],
                         mock_os_exists.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d', 'fake_basename'),
                          mock.call('/etc/udev/rules.d', 'not_a_rule'),
                          mock.call('/etc/udev/rules.d', 'fake.rules'),
                          mock.call('/etc/udev/rules.d', 'fake_err.rules'),
                          mock.call('/etc/udev/rules.d', 'dir')],
                         mock_os_join.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d/fake.rules',
                                    '/etc/udev/rules.d/fake.renamedrule'),
                          mock.call('/etc/udev/rules.d/fake_err.rules',
                                    '/etc/udev/rules.d/fake_err.renamedrule')],
                         mock_os_rename.call_args_list)
        mock_os_symlink.assert_called_once_with(
            '/etc/udev/rules.d/fake_basename',
            '/etc/udev/rules.d/fake.rules')
        self.assertEqual([mock.call('udevadm', 'settle', '--quiet'),
                          mock.call('udevadm', 'settle', '--quiet'),
                          mock.call('udevadm', 'control', '--reload-rules',
                                    check_exit_code=[0])],
                         mock_execute.call_args_list)

    @mock.patch.object(utils.os.path, 'exists')
    @mock.patch.object(utils.os.path, 'islink')
    @mock.patch.object(utils.os.path, 'isdir')
    @mock.patch.object(utils.os.path, 'join')
    @mock.patch.object(utils.os, 'listdir')
    @mock.patch.object(utils.os, 'remove')
    @mock.patch.object(utils.os, 'rename')
    @mock.patch.object(utils, 'execute')
    def test_unblacklist_udev_rules(self, mock_execute, mock_os_rename,
                                    mock_os_remove, mock_os_listdir,
                                    mock_os_join, mock_os_isdir,
                                    mock_os_islink, mock_os_exists):
        def _fake_join(path1, path2):
            return '{0}/{1}'.format(path1, path2)

        mock_os_join.side_effect = _fake_join
        mock_os_listdir.return_value = [
            'not_a_rule', 'fake.rules', 'fake_err.rules', 'fake.renamedrule',
            'fake_err.renamedrule', 'dir']
        mock_os_rename.side_effect = [None, OSError]
        mock_os_remove.side_effect = [None, OSError]
        mock_os_isdir.side_effect = [False] * 5 + [True]
        mock_os_exists.return_value = True
        mock_os_islink.return_value = True
        utils.unblacklist_udev_rules()
        self.assertEqual([mock.call('/etc/udev/rules.d', 'not_a_rule'),
                          mock.call('/etc/udev/rules.d', 'fake.rules'),
                          mock.call('/etc/udev/rules.d', 'fake_err.rules'),
                          mock.call('/etc/udev/rules.d', 'fake.renamedrule'),
                          mock.call('/etc/udev/rules.d',
                                    'fake_err.renamedrule'),
                          mock.call('/etc/udev/rules.d', 'dir')],
                         mock_os_join.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d/not_a_rule'),
                          mock.call('/etc/udev/rules.d/fake.rules'),
                          mock.call('/etc/udev/rules.d/fake_err.rules'),
                          mock.call('/etc/udev/rules.d/fake.renamedrule'),
                          mock.call('/etc/udev/rules.d/fake_err.renamedrule'),
                          mock.call('/etc/udev/rules.d/dir')],
                         mock_os_isdir.call_args_list)
        expected_rules_calls = [mock.call('/etc/udev/rules.d/fake.rules'),
                                mock.call('/etc/udev/rules.d/fake_err.rules')]
        self.assertEqual(expected_rules_calls,
                         mock_os_islink.call_args_list)
        self.assertEqual(expected_rules_calls,
                         mock_os_remove.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d/fake.renamedrule'),
                          mock.call('/etc/udev/rules.d/fake_err.renamedrule')],
                         mock_os_exists.call_args_list)
        self.assertEqual([mock.call('/etc/udev/rules.d/fake.renamedrule',
                                    '/etc/udev/rules.d/fake.rules'),
                          mock.call('/etc/udev/rules.d/fake_err.renamedrule',
                                    '/etc/udev/rules.d/fake_err.rules')],
                         mock_os_rename.call_args_list)
        self.assertEqual([mock.call('udevadm', 'settle', '--quiet'),
                          mock.call('udevadm', 'settle', '--quiet'),
                          mock.call('udevadm', 'control', '--reload-rules',
                                    check_exit_code=[0]),
                          mock.call('udevadm', 'trigger',
                                    '--subsystem-match=block',
                                    check_exit_code=[0]),
                          mock.call('udevadm', 'settle', '--quiet',
                                    check_exit_code=[0])],
                         mock_execute.call_args_list)
