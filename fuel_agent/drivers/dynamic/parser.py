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

import copy

from fuel_agent.drivers.dynamic import adapters
from fuel_agent.drivers.dynamic import references
from fuel_agent import objects

from fuel_agent.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class Node(object):
    """Stores information from node."""


class ParserError(Exception):
    """General parsing error"""


class DuplicatedDeviceError(ParserError, ValueError):
    """Raised when device was already used"""


class DynamicPartitionFormat(object):

    MD = 'md'
    PARTED = 'parted'
    PARTITION = 'parition'

    def __init__(self, partition_data, node):
        self._raw_data = copy.deepcopy(partition_data)
        self._used_devices = set()
        self.references = references.References()
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
            except references.DuplicatedReferenceError as e:
                LOG.exception(e)
                raise ParserError(
                    'Duplicated ID {0} for MD object'.format(md_id)
                )

        return mds

    def _add_partition_reference(self, parted, partition):
        full_id = '{parted_id}/{obj_type}/partition_id'.format(
            parted_id=parted.id,
            obj_type=self.PARTITION,
            partition_id=partition.id,
        )
        try:
            self.references.add(self.PARTED, full_id, partition, strict=True)
        except references.DuplicatedReferenceError as e:
            LOG.exception(e)
            raise ParserError(
                'Duplicated ID {partition_id} for Partition in Parted '
                '(ID {parted_id}) object'.format(
                    partition_id=partition.id,
                    parted_id=parted.id)
            )

    def parse_parteds(self):
        raw_parteds = self._raw_data.get('parteds', [])
        parteds = []

        for parted_data in raw_parteds:
            parted = adapters.PartedAdapter(parted_data)

            try:
                for partition in parted.partitions:

                    self._add_partition_reference(parted, partition)

                self.mark_device_as_used(parted.name)
                parteds.append(parted)
                self.references.add(self.PARTED, parted.id,
                                    parted, strict=True)

            except references.DuplicatedReferenceError as e:
                LOG.exception(e)
                raise ParserError(
                    'Duplicated ID {0} for Parted object'.format(parted.id)
                )
        return parteds
