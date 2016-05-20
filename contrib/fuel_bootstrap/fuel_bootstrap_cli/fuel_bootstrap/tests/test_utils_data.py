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
import copy

import mock
import unittest2

from fuel_bootstrap import consts
from fuel_bootstrap import errors
from fuel_bootstrap.utils import data as bs_data
from fuel_bootstrap.utils.data import BootstrapDataBuilder

DATA = {'ubuntu_release': 'trusty',
        'repos': ['deb http://archive.ubuntu.com/ubuntu suite'],
        'http_proxy': None,
        'https_proxy': None,
        'direct_repo_addr': ['/test_repo_addr'],
        'post_script_file': None,
        'root_ssh_authorized_file': '/root/test',
        'extra_dirs': ['/test_extra_dirs'],
        'packages': ['test_package'],
        'label': None,
        'no_default_extra_dirs': '/test_no_default_extra_dirs',
        'no_default_packages': 'test_no_default_packages',
        'extend_kopts': 'test_extend_kopts',
        'kernel_flavor': 'test_kernel_flavor',
        'output_dir': '/test_dir',
        'certs': None,
        'root_password': '1234567_abc'
        }

BOOTSTRAP_MODULES = [
    {'name': 'kernel',
     'mask': 'kernel',
     'uri': 'http://127.0.0.1:8080/bootstraps/123/vmlinuz'},
    {'name': 'initrd',
     'mask': 'initrd',
     'compress_format': 'xz',
     'uri': 'http://127.0.0.1:8080/bootstraps/123/initrd.img'},
    {'name': 'rootfs',
     'mask': 'rootfs',
     'compress_format': 'xz',
     'uri': 'http://127.0.0.1:8080/bootstraps/123/root.squashfs',
     'format': 'ext4',
     'container': 'raw'}
]

REPOS = [{'name': 'repo_0',
          'type': 'deb',
          'uri': 'http://archive.ubuntu.com/ubuntu',
          'priority': None,
          'suite': 'suite',
          'section': ''}]

IMAGE_DATA = {'/': {'name': 'rootfs',
                    'mask': 'rootfs',
                    'compress_format': 'xz',
                    'uri': 'http://127.0.0.1:8080/bootstraps/123/'
                           'root.squashfs',
                    'format': 'ext4',
                    'container': 'raw'}}


class DataBuilderTestCase(unittest2.TestCase):
    def setUp(self):
        super(DataBuilderTestCase, self).setUp()
        self.bd_builder = BootstrapDataBuilder(DATA)
        self.bd_builder.uuid = 123

    def test_build(self):
        extra_dirs = DATA.get('extra_dirs')

        proxy_settings = {}
        packages = ['test_package',
                    'test_kernel_flavor']
        bootstrap = {
            'bootstrap': {
                'modules': BOOTSTRAP_MODULES,
                'extend_kopts': self.bd_builder.extend_kopts,
                'post_script_file': self.bd_builder.post_script_file,
                'uuid': self.bd_builder.uuid,
                'extra_files': extra_dirs,
                'root_ssh_authorized_file':
                    self.bd_builder.root_ssh_authorized_file,
                'container': {
                    'meta_file': consts.METADATA_FILE,
                    'format': self.bd_builder.container_format
                },
                'label': self.bd_builder.label,
                'certs': self.bd_builder.certs
            },
            'repos': REPOS,
            'proxies': proxy_settings,
            'codename': self.bd_builder.ubuntu_release,
            'output': self.bd_builder.output,
            'packages': packages,
            'image_data': IMAGE_DATA,
            'hashed_root_password': self.bd_builder.hashed_root_password,
            'root_password': self.bd_builder.root_password,
        }
        self.assertItemsEqual(self.bd_builder.build(), bootstrap)

    def test_get_extra_dirs_no_default(self):
        result = self.bd_builder._get_extra_dirs()
        self.assertEqual(result, DATA.get('extra_dirs'))

    @mock.patch.object(bs_data, 'CONF')
    def test_get_extra_dirs(self, conf_mock):
        self.bd_builder.no_default_extra_dirs = None
        conf_mock.extra_dirs = ['/conf_test_extra_dirs']
        result = self.bd_builder._get_extra_dirs()
        self.assertItemsEqual(result, ['/test_extra_dirs',
                                       '/conf_test_extra_dirs'])

    def test_prepare_modules(self):
        result = self.bd_builder._prepare_modules()
        self.assertEqual(result, BOOTSTRAP_MODULES)

    def test_prepare_image_data(self):
        result = self.bd_builder._prepare_image_data()
        self.assertEqual(result, IMAGE_DATA)

    def test_get_no_proxy_settings(self):
        self.assertEqual(self.bd_builder._get_proxy_settings(), {})

    def test_get_proxy_settings(self):
        self.bd_builder.http_proxy = 'http_proxy'
        self.bd_builder.https_proxy = 'https_proxy'

        proxy = {'protocols': {'http': self.bd_builder.http_proxy,
                               'https': self.bd_builder.https_proxy},
                 'direct_repo_addr_list': ['/test_repo_addr']}
        result = self.bd_builder._get_proxy_settings()
        self.assertEqual(result, proxy)

    def test_get_direct_repo_addr_no_default(self):
        self.bd_builder.no_default_direct_repo_addr = 'no_default'
        result = self.bd_builder._get_direct_repo_addr()
        self.assertEqual(result, DATA.get('direct_repo_addr'))

    @mock.patch.object(bs_data, 'CONF')
    def test_get_direct_repo_addr_conf(self, conf_mock):
        conf_mock.direct_repo_addresses = ['/conf_test_repo_addr']
        result = self.bd_builder._get_direct_repo_addr()
        self.assertItemsEqual(result, ['/conf_test_repo_addr',
                                       '/test_repo_addr'])

    def test_get_direct_repo_addr(self):
        result = self.bd_builder._get_direct_repo_addr()
        self.assertEqual(result, DATA.get('direct_repo_addr'))

    @mock.patch.object(bs_data, 'CONF')
    def test_get_repos_conf(self, conf_mock):
        self.bd_builder.repos = []
        conf_mock.repos = REPOS
        self.assertEqual(self.bd_builder._get_repos(), conf_mock.repos)

    def test_get_repos(self):
        self.assertEqual(self.bd_builder._get_repos(), REPOS)

    def test_get_packages(self):
        packages = ['test_package',
                    'test_kernel_flavor']
        self.assertItemsEqual(self.bd_builder._get_packages(), packages)

    @mock.patch.object(bs_data, 'CONF')
    def test_get_packages_not_no_default(self, conf_mock):
        self.bd_builder.no_default_packages = None
        conf_mock.packages = ['conf_package']
        result_packages = ['test_package',
                           'test_kernel_flavor',
                           'conf_package']
        self.assertItemsEqual(self.bd_builder._get_packages(), result_packages)

    def parse_incorrect(self, repo):
        name = 'repo_0'
        error_msg = ("Couldn't parse repository '{0}'"
                     .format(repo))
        with self.assertRaises(errors.IncorrectRepository, msg=error_msg):
            BootstrapDataBuilder._parse_repo(repo, name)

    def test_parse_incorrect_type(self):
        repo = 'deb-false http://archive.ubuntu.com/ubuntu codename'
        self.parse_incorrect(repo)

    def test_parse_empty_uri(self):
        repo = 'deb codename'
        self.parse_incorrect(repo)

    def test_parse_empty_suite(self):
        repo = 'deb http://archive.ubuntu.com/ubuntu'
        self.parse_incorrect(repo)

    def parse_correct(self, repo, return_repo):
        name = 'repo_0'
        result = BootstrapDataBuilder._parse_repo(repo, name)
        self.assertEqual(result, return_repo)

    def test_parse_correct_necessary(self):
        repo = DATA.get('repos')[0]
        self.parse_correct(repo, REPOS[0])

    def test_parse_correct_section(self):
        repo = 'deb http://archive.ubuntu.com/ubuntu suite section'
        return_repo = copy.deepcopy(REPOS[0])
        return_repo['section'] = 'section'
        self.parse_correct(repo, return_repo)

    def test_parse_correct_priority(self):
        repo = 'deb http://archive.ubuntu.com/ubuntu suite ,1'
        return_repo = copy.deepcopy(REPOS[0])
        return_repo['priority'] = '1'
        self.parse_correct(repo, return_repo)

    def test_parse_correct_all(self):
        repo = 'deb http://archive.ubuntu.com/ubuntu suite section,1'
        return_repo = copy.deepcopy(REPOS[0])
        return_repo['section'] = 'section'
        return_repo['priority'] = '1'
        self.parse_correct(repo, return_repo)
