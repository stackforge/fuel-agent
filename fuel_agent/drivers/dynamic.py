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

import collections
import copy

from fuel_agent import objects
from fuel_agent.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class Node(object):
    """Stores information from node."""


class ReferenceError(Exception):
    """General reference error"""


class DuplicatedReferenceError(ReferenceError, KeyError):
    """Reference already exists"""


class References(object):
    """Keeps references to objects"""

    def __init__(self):
        self._refs = collections.defaultdict(dict)

    @classmethod
    def _format_reference(cls, obj_type, obj_id):
        return '{type}/{id}'.format(type=obj_type, id=obj_id)

    @classmethod
    def _parse_reference(cls, reference):
        return reference.split('/', 1)

    def add(self, obj_type, obj_id, obj, strict=False):
        if strict and obj_id in self._refs[obj_type]:
            raise DuplicatedReferenceError(
                "Reference '{0}' already exists".format(
                    self._format_reference(obj_type, obj_id)
                ))

        self._refs[obj_type][obj_id] = obj

    def get(self, obj_type, obj_id):
        return self._refs[obj_type].get(obj_id)

    def get_by_type(self, obj_type):
        return self._refs[obj_type].values()

    def __getitem__(self, reference):
        obj_type, obj_id = self._parse_reference(reference)
        return self.get(obj_type, obj_id)

    def __setitem__(self, reference, obj):
        obj_type, obj_id = self._parse_reference(reference)
        self.add(obj_type, obj_id, obj)


class ParserError(Exception):
    """General parsing error"""


class DuplicatedDeviceError(ParserError, ValueError):
    """Raised when device was already used"""


class DynamicPartitionFormat(object):

    MD = 'md'

    def __init__(self, partition_data, node):
        self._raw_data = copy.deepcopy(partition_data)
        self._used_devices = set()
        self.references = References()
        self._node = node

    def is_device_used(self, device):
        return device in self._used_devices

    def mark_device_as_used(self, device):
        if self.is_device_used(device):
            raise DuplicatedDeviceError(
                "Device '{0}' is already used".format(device))
        self._used_devices.add(device)

    def parse_mds(self):
        raw_mds = self._raw_data.get('mds', [])
        mds = []

        for raw_md in raw_mds:
            md_id = raw_md.pop('id')
            try:
                md = objects.MD.from_dict(raw_md)

                for device in md.all_devices:
                    self.mark_device_as_used(device)

                mds.append(md)

                self.references.add(self.MD, md_id, md, strict=True)
            except DuplicatedReferenceError as e:
                LOG.exception(e)
                raise ParserError(
                    'Duplicated ID {0} for MD object'.format(md_id)
                )

        return mds
