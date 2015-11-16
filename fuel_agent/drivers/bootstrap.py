# Copyright 2014 Mirantis, Inc.
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

import itertools
import math
import os
import copy
import uuid

from oslo_config import cfg
import six
import yaml

from fuel_agent import errors
from fuel_agent import objects
from fuel_agent.openstack.common import log as logging
import ipdb;ipdb.set_trace()
LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class BaseDataDriver(object):
    """Data driver API

    For example, data validation methods,
    methods for getting object schemes, etc.
    """

    def __init__(self, data):
        self.data = copy.deepcopy(data)

    @property
    def operating_system(self):
        """Returns instance of OperatingSystem object"""


class MakeBootstrap(BaseDataDriver):
    """Driver for parsing regular """

    # Packages required for the master node to discover a bootstrap node
    # Hardcoded list used for disable user-factor : when user can accidentally
    # remove fuel-required packages, and create totally non-working bootstrap
    FUEL_PKGS_DFLT = [
        "openssh-client",
        "openssh-server",
        "ntp",
        "mcollective",
        "nailgun-agent",
        "nailgun-mcagents",
        "network-checker",
        "fuel-agent"
    ]

    def __init__(self, data):
        import ipdb;ipdb.set_trace()
        super(MakeBootstrap, self).__init__(data)
        self._partition_scheme = objects.PartitionScheme()
        self._image_scheme = self.parse_image_scheme()

        # Packages required for ubuntu, also includes kernel-related:
        ubuntu_pkgs_default = [
            "ubuntu-minimal",
            "live-boot",
            "live-boot-initramfs-tools",
            "wget",
            "biosdevname",
            "linux-image-{0}".format(self.data.get('kernel_flavor',
                                                   'generic-lts-trusty')),
            "linux-firmware",
            "linux-firmware-nonfree",
            "xz-utils",
            "squashfs-tools",
            "msmtp-mta"
        ]

        self.data['packages'] = self.data.get('packages', [])
        self.data['packages'].extend(ubuntu_pkgs_default + self.FUEL_PKGS_DFLT)

        self._operating_system = self.parse_operating_system()

    @property
    def operating_system(self):
        return self._operating_system

    @property
    def partition_scheme(self):
        return self._partition_scheme

    @property
    def image_scheme(self):
        return self._image_scheme

    def parse_image_scheme(self):
        LOG.debug('--- Preparing image scheme ---')
        data = self.data
        image_meta = self._image_meta
        image_scheme = objects.ImageScheme()
        # We assume for every file system user may provide a separate
        # file system image. For example if partitioning scheme has
        # /, /boot, /var/lib file systems then we will try to get images
        # for all those mount points. Images data are to be defined
        # at provision.json -> ['ks_meta']['image_data']
        LOG.debug('Looping over all images in provision data')
        for mount_point, image_data in six.iteritems(
                data['ks_meta']['image_data']):
            LOG.debug('Adding image for fs %s: uri=%s format=%s container=%s' %
                      (mount_point, image_data['uri'],
                       image_data['format'], image_data['container']))
            iname = os.path.basename(urlparse(image_data['uri']).path)
            imeta = next(itertools.chain(
                (img for img in image_meta.get('images', [])
                 if img['container_name'] == iname), [{}]))
            image_scheme.add_image(
                uri=image_data['uri'],
                target_device=self.partition_scheme.fs_by_mount(
                    mount_point).device,
                format=image_data['format'],
                container=image_data['container'],
                size=imeta.get('raw_size'),
                md5=imeta.get('raw_md5'),
            )
        return image_scheme

    def parse_operating_system(self):
        if self.data.get('codename').lower() != 'trusty':
            raise errors.WrongInputDataError(
                'Currently, only Ubuntu Trusty is supported, given '
                'codename is {0}'.format(self.data.get('codename')))

        #FIXME
        packages = self.data.get('packages', self.FUEL_PKGS_DFLT)

        repos = []
        for repo in self.data['repos']:
            repos.append(objects.DEBRepo(
                name=repo['name'],
                uri=repo['uri'],
                suite=repo['suite'],
                section=repo['section'],
                priority=repo['priority']))

        proxies = objects.RepoProxies()

        proxy_dict = self.data.get('proxies', {})
        for protocol, uri in six.iteritems(proxy_dict.get('protocols', {})):
            proxies.add_proxy(protocol, uri)
        proxies.add_direct_repo_addrs(proxy_dict.get(
            'direct_repo_addr_list', []))

        os = objects.Ubuntu(repos=repos, packages=packages, major=14, minor=4,
                            proxies=proxies)
        return os

    def parse_schemes(self):
        # Check for predetermined uuid
        if 'uuid' not in self.data:
            self.data['uuid'] = six.text_type(uuid.uuid4())
            LOG.info('No predefined UUID, generating new UUID:'
                     ' {0}'.format(self.data['uuid']))
        if 'extend_kopts' not in self.data:
            self.data['extend_kopts'] = None
            (LOG.warning('Additional kernel options are not defined, '
                         'using default'))

        # Currently we can use only one build scheme, so
        # just append input data.
        # And also, currently we don't use uri format - but lets use
        # one format, for future implementation.

        m_kernel = {
            'uri': 'http://127.0.0.1:8080/bootstraps/{0}/vmlinuz'.format(
                self.data['uuid'])}
        m_initrd = {
            'compress_format': 'xz',
            'uri': 'http://127.0.0.1:8080/bootstraps/{0}/initrd.img'.format(
                self.data['uuid'])}
        m_rootfs = {
            'compress_format': 'xz',
            'uri': 'http://127.0.0.1:8080/bootstraps/{0}/root.squashfs'.format(
                self.data['uuid']),
            'format': 'ext4', 'container': 'gzip'}

        self.data['bootstrap_modules'] = {
            'm_kernel': m_kernel,
            'm_initrd': m_initrd,
            'm_rootfs': m_rootfs
        }

        self.data['meta_file'] = 'metadata.yaml'
        self.data['container'] = 'tar.gz'

        # Actually, we need only / system for build.
        # so lets create it with existing funcs:
        self.data['image_data'] = {"/": m_rootfs}
        super(MakeBootstrap, self).parse_schemes()
