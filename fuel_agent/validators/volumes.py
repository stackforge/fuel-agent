# Copyright 2015 Mirantis, Inc.
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

import copy
import itertools
import jsonschema

from fuel_agent import errors
from fuel_agent.openstack.common import log as logging
from fuel_agent.validators.base import BaseValidator


LOG = logging.getLogger(__name__)


class SimpleNailgunDriverValidator(BaseValidator):

    schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Volume Management Metadata',
        'type': 'object',
        'definitions': {
            'pathPattern': {
                'pattern': '^((\/)|((\/[^\/]+)+))$',
                'type': 'string',
            },
            'fileSystems': {
                'type': 'string',
                'enum': [
                    'fat16',
                    'fat32',
                    'ntfs',
                    'ext2',
                    'ext3',
                    'ext4',
                    'jfs',
                    'xfs',
                    'swap',
                ],
            },
        },
        'properties': {
            'pvs': {
                'title': 'Physical Volumes',
                'type': 'array',
                'items': {
                    'title': 'Physical Volume',
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                        },
                        'metadatacopies': {
                            'type': 'integer',
                        },
                        'metadatasize': {
                            'type': 'integer',
                        },
                    },
                },
            },
            'lvs': {
                'title': 'Logical Volumes',
                'type': 'array',
                'items': {
                    'name': {
                        'description': 'name of lvm',
                        'type': 'string',
                    },
                    'size': {
                        'description': 'size of LV in bytes',
                        'type': 'integer',
                    },
                    'vgname': {
                        'description': 'name of VG that LV belongs to',
                        'type': 'string'
                    },
                },
            },
            'fss': {
                'title': 'File Systems',
                'type': 'array',
                'items': {
                    'device': {
                        '$ref': '#definitions/pathPattern',
                    },
                    'mount': {
                        'description': 'Mount point',
                        'type': 'string'
                    },
                    'fs_type': {
                        '$ref': '#definitions/fileSystems',
                    },
                    'fs_options': {
                        'type': 'string',
                    },
                    'fs_label': {
                        'type': 'string',
                    },
                },
            },
            'parteds': {
                'title': 'Parteds',
                'type': 'array',
                'items': {
                    'name': {
                        '$ref': '#definitions/pathPattern',
                    },
                    'label': {
                        'type': 'string',
                    },
                    'partitions': {
                        'type': 'array',
                        'items': {
                            'name': {
                                'type': 'string',
                            },
                            'label': {
                                'type': 'string',
                            },
                            'device': {
                                '$ref': '#definitions/pathPattern',
                            },
                            'begin': {
                                'type': 'integer',
                            },
                            'end': {
                                'type': 'integer',
                            },
                            'guid': {
                                'type': 'string'
                            },
                        },
                    },
                },
            },
            'mds': {
                'title': 'Multiple Devices',
                'type': 'array',
                'items': {
                    'level': {
                        'type': 'string',
                    },
                    'name': {
                        '$ref': '#definitions/pathPattern',
                    },
                    'devices': {
                        'type': 'array',
                        'items': {
                            '$ref': '#definitions/pathPattern',
                        },
                    },
                    'spares': {
                        'type': 'array',
                        'items': {
                            '$ref': '#definitions/pathPattern',
                        },
                    },
                },
            },
            'vgs': {
                'title': 'Volume Groups',
                'type': 'array',
                'items': {
                    'name': {
                        'type': 'string',
                    },
                    'pvnames': {
                        'description': 'List of names of Physical Volumes',
                        'type': 'array',
                        'items': {
                            '$ref': '#definitions/pathPattern',
                        },
                    },
                },
            },
        }
    }

    @property
    def partitions(self):
        return [y for y in itertools.chain.from_iterable(
            x['partitions'] for x in self.data.get('parteds', []))]

    @classmethod
    def raise_error(self, message):
        error = errors.WrongPartitionSchemeError(message)
        LOG.exception(error)
        raise error

    def validate(self, data):
        self.data = copy.deepcopy(data)
        self.validate_schema()
        self.validate_partitions()
        self.validate_pvs()
        self.validate_vgs()
        self.validate_lvs()
        self.validate_fss()

    def validate_schema(self):
        checker = jsonschema.FormatChecker()
        jsonschema.validate(self.data, self.schema, format_checker=checker)

    def validate_partitions(self):
        for partition in self.partitions:
            if partition['begin'] >= partition['end']:
                self.raise_error(
                    "Starting point on {0} partition is greater than the end "
                    "point.\nbegin({1}) > end({2})".format(partition['name'],
                                                           partition['begin'],
                                                           partition['end']))

    def validate_pvs(self):
        partition_devices = set(prt.get('name') for prt in self.partitions)
        for pv in self.data.get('pvs', []):
            if pv['name'] not in partition_devices:
                self.raise_error(
                    "Physical Volume cannot be assigned to not existing "
                    "partition.\n'{0}' not in {1}".format(pv['name'],
                                                          partition_devices))

    def validate_vgs(self):
        existing_pvs = set(pv['name'] for pv in self.data.get('pvs', []))
        for vg in self.data.get('vgs', []):
            for pvname in vg['pvnames']:
                if pvname not in existing_pvs:
                    self.raise_error(
                        "Volume Group is trying to use non-existing "
                        "Physical Volume.\n{0} not in {1}".format(pvname,
                                                                  existing_pvs)
                    )

    def validate_lvs(self):
        vg_names = set(vg['name'] for vg in self.data.get('vgs', []))
        for lv in self.data.get('lvs', []):
            if lv['vgname'] not in vg_names:
                self.raise_error(
                    "Logical Volume is trying to use non-existing "
                    "Volume Group.\n{0} not in {1}".format(lv['vgname'],
                                                           vg_names))

    def validate_fss(self):
        pass
