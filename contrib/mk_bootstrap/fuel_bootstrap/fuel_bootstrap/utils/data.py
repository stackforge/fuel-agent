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

import re
import six
import uuid
import yaml

from fuel_bootstrap import consts
from fuel_bootstrap import errors

# Packages required for the master node to discover a bootstrap node
# Hardcoded list used for disable user-factor : when user can accidentally
# remove fuel-required packages, and create totally non-working bootstrap
FUEL_DEFAULT_PACKAGES = [
    "openssh-client",
    "openssh-server",
    "ntp",
    "mcollective",
    "nailgun-agent",
    "nailgun-mcagents",
    "network-checker",
    "fuel-agent"
]

UBUNTU_DEFAULT_PACKAGES = [
    "ubuntu-minimal",
    "live-boot",
    "live-boot-initramfs-tools",
    "wget",
    "biosdevname",
    "linux-firmware",
    "linux-firmware-nonfree",
    "xz-utils",
    "squashfs-tools",
    "msmtp-mta"
]


class BootstrapDataBuilder(object):

    def __init__(self, kwargs):
        self.astute = self._parse_astute()

        self.uuid = six.text_type(uuid.uuid4())

        self.bootstrap_modules = self._get_bootstrap_modules()

        # output file-name for meta file
        self.metafile = consts.METADATA_FILE

        # format for output arhive - which contain all files
        self.container = 'tar.gz'

        # Actually, we need only / system for install base system
        # so lets create it with existing funcs:
        self.image_data = {"/": self._get_m_rootfs()}

        self.ubuntu_release = kwargs.ubuntu_release or 'trusty'
        self.ubuntu_repo = kwargs.ubuntu_repo
        self.mos_repo = kwargs.mos_repo
        self.repos = kwargs.repos or []

        self.http_proxy = kwargs.http_proxy or \
            self.astute['BOOTSTRAP']['HTTP_PROXY']
        self.https_proxy = kwargs.https_proxy or \
            self.astute['BOOTSTRAP']['HTTPS_PROXY']
        self.direct_repo_addr = kwargs.direct_repo_addr

        self.post_script_file = kwargs.post_script_file
        self.include_kernel_module = kwargs.include_kernel_module
        self.blacklist_kernel_module = kwargs.blacklist_kernel_module

        self.packages = kwargs.packages
        self.packages_list_file = kwargs.package_list_file

        self.label = kwargs.label
        self.inject_files_from = kwargs.inject_files_from
        self.extend_kopts = kwargs.extend_kopts

        self.kernel_flavor = kwargs.kernel_flavor
        self.ssh_keys = kwargs.ssh_keys
        self.output_dir = kwargs.output_dir

    def _parse_astute(self):
        # TODO(asvechnikov): remove hardcode
        with open('/etc/fuel/astute.yaml') as f:
            data = yaml.load(f)
        return data

    def build(self):
        return {
            'repos': self._get_repos(),
            'proxies': self._get_proxy_settings(),
            'codename': self.ubuntu_release,
            'output': self.output_dir,
            'kernel_flavor': self.kernel_flavor,
            'extend_kopts': self.extend_kopts,
            'packages': self._get_packages(),
            'uuid': self.uuid,
            'bootstrap_modules': self._get_bootstrap_modules(),
            'meta_file': self.metafile,
            'container': self.container,
            'image_data': self.image_data
        }

    def _get_bootstrap_modules(self):
        # Currently we can use only one build scheme, so
        # just append input data.
        # And also, currently we don't use uri format - but lets use
        # one format, for future implementation.
        m_kernel = {
            'uri': "http://127.0.0.1:8080/bootstraps/{0}/vmlinuz"
                   .format(self.uuid)
        }
        m_initrd = {
            'compress_format': 'xz',
            'uri': "http://127.0.0.1:8080/bootstraps/{0}/initrd.img"
                   .format(self.uuid)
        }

        # m_rootfs configuration also used for creating chrooted base system
        # with manager.install_base_os(). So its only one point for
        # passing 'format' and 'container' variables.
        m_rootfs = self._get_m_rootfs()
        return {'m_kernel': m_kernel,
                'm_initrd': m_initrd,
                'm_rootfs': m_rootfs}

    def _get_m_rootfs(self):
        return {'compress_format': 'xz',
                'uri': "http://127.0.0.1:8080/bootstraps/{0}/root.squashfs"
                       .format(self.uuid),
                'format': 'ext4',
                'container': 'raw'}

    def _get_proxy_settings(self):
        if self.http_proxy or self.https_proxy:
            return {'protocols': {'http': self.http_proxy,
                                  'https': self.https_proxy},
                    'direct_repo_addr_list': self._get_direct_repo_addr()}
        return {}

    def _get_direct_repo_addr(self):
        addrs = set()
        if self.direct_repo_addr:
            addrs |= set(self.direct_repo_addr)

        addrs.add(self.astute['ADMIN_NETWORK']['ipaddress'])

        return list(addrs)

    def _get_repos(self):
        repos = []
        if self.ubuntu_repo:
            repos.extend(self._parse_ubuntu_repos(self.ubuntu_repo))
        else:
            repos.extend(self.astute['BOOTSTRAP']['MIRROR_DISTRO'])

        if self.mos_repo:
            repos.extend(self._parse_mos_repos(self.mos_repo))
        else:
            repos.extend(self.astute['BOOTSTRAP']['MIRROR_MOS'])

        repo_count = 0
        for repo in self.repos:
            repo_count += 1
            repos.append(self._parse_repo(
                repo,
                name="extra_repo{0}".format(repo_count)))

        if not self.repos:
            repos.extend(self.astute['BOOTSTRAP']['EXTRA_DEB_REPOS'])

        return sorted(repos,
                      key=lambda repo: repo['priority'] or 500,
                      reverse=True)

    def _get_packages(self):
        result = set(FUEL_DEFAULT_PACKAGES + UBUNTU_DEFAULT_PACKAGES)
        result.add("linux-image-{0}".format(self.kernel_flavor))
        if self.packages:
            result |= set(self.packages)
        if self.packages_list_file:
            with open(self.packages_list_file) as f:
                result |= set(f.readlines())
        return list(result)

    @classmethod
    def _parse_not_extra_repo(cls, repo):
        regexp = r"(?P<uri>[^\s]+) (?P<suite>[^\s]+)"

        match = re.match(regexp, repo)

        if not match:
            raise errors.IncorrectRepository(
                "Coulnd't parse ubuntu repository {0}".
                format(repo)
            )

        return match.group('uri', 'suite')

    @classmethod
    def _parse_mos_repos(cls, repo):
        uri, suite = cls._parse_not_extra_repo(repo)

        result = cls._generate_repos_from_uri(
            uri=uri,
            codename=suite,
            name='mos',
            components=['', '-updates', '-security'],
            section='main restricted',
            priority='1050'
        )
        result += cls._generate_repos_from_uri(
            uri=uri,
            codename=suite,
            name='mos',
            components=['-holdback'],
            section='main restricted',
            priority='1100'
        )
        return result

    @classmethod
    def _parse_ubuntu_repos(cls, repo):
        uri, suite = cls._parse_not_extra_repo(repo)

        return cls._generate_repos_from_uri(
            uri=uri,
            codename=cls.ubuntu_release,
            name='ubuntu',
            components=['', '-updates', '-security'],
            section='main universe multiverse'
        )

    @classmethod
    def _generate_repos_from_uri(cls, uri, codename, name, components=None,
                                 section=None, type_=None, priority=None):
        if not components:
            components = ['']
        result = []
        for component in components:
            result.append({
                "name": "{0}{1}".format(name, component),
                "type": type_ or "deb",
                "uri": uri,
                "priority": priority,
                "section": section,
                "suite": "{0}{1}".format(codename, component)
            })
        return result

    @classmethod
    def _parse_repo(cls, repo, name=None):
        regexp = r"(?P<type>deb(-src)?) (?P<uri>[^\s]+) (?P<suite>[^\s]+)( "\
                 r"(?P<section>[\w\s]*))?(,(?P<priority>[\d]+))?"

        match = re.match(regexp, repo)

        if not match:
            raise errors.IncorrectRepository("Couldn't parse repository '{0}'"
                                             .format(repo))

        repo_type = match.group('type')
        repo_suite = match.group('suite')
        repo_section = match.group('section')
        repo_uri = match.group('uri')
        repo_priority = match.group('priority')

        return {'name': name,
                'type': repo_type,
                'uri': repo_uri,
                'priority': repo_priority,
                'suite': repo_suite,
                'section': repo_section or ''}
