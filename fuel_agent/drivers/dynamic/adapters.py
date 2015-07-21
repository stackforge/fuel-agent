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

from fuel_agent import objects


class BaseAdapter(object):

    def __init__(self, data):
        self._data = copy.deepcopy(data)
        self.id = self._data.pop('id')


class PartedAdapter(BaseAdapter):
    """Intermediate object for parsing raw Parted data passed to driver."""

    def __init__(self, data):
        super(self.__class__, self).__init__(data)

        partitions_data = self._data.pop('partitions', [])
        self.partitions = []

        self.obj = objects.Parted.from_dict(self._data)

        for partition_data in partitions_data:
            partition_adapter = PartitionAdapter(partition_data)
            self.obj.add_partition(**partition_adapter.parsed_data)
            self.partitions.append(partition_adapter)

    @property
    def name(self):
        return self.obj.name


class PartitionAdapter(BaseAdapter):
    """Intermediate object for parsing raw Partion data passed to driver."""

    def __init__(self, data):
        super(self.__class__, self).__init__(data)

        size = self._data.pop('size', None)
        if self.end and self.begin:
            size = self.end - self.begin

        if isinstance(size, dict):
            self.min_size = size['min']
            self.best_size = size['best']
            self.max_size = size['max']
        elif size is not None:
            self.min_size = self.best_size = self.max_size = size

        self.size = self.min_size

    @property
    def begin(self):
        return self._data.get('begin')

    @property
    def end(self):
        return self._data.get('end')

    @property
    def parsed_data(self):
        data = copy.deepcopy(self._data)

        if self.end and self.begin:
            data.update(
                begin=self.begin,
                end=self.end,
            )
        else:
            data.update(size=self.size)

        return data
