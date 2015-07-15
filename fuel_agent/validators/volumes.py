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
import six

from fuel_agent import consts
from fuel_agent.errors import WrongPartitionSchemeError
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
                'pattern': consts.PATH_REGEXP,
                'type': 'string',
            },
            'fileSystems': {
                'type': 'string',
                'enum': [
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
                            'type': 'number',
                        },
                        'metadatasize': {
                            'type': 'number',
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
                    'minsize': {
                        'description': 'minsize of LV in bytes',
                        'type': 'number',
                    },
                    'bestsize': {
                        'description': 'bestsize of LV in bytes',
                        'type': 'number',
                    },
                    'maxsize': {
                        'description': 'maxsize of LV in bytes',
                        'type': 'number',
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
                                'type': 'number',
                                'minimum': 1,
                            },
                            'end': {
                                'type': 'number',
                                'minimum': 2,
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
        return itertools.chain.from_iterable(
            x['partitions'] for x in self.data.get('parteds', []))

    def get_all_devices(self):
        devices = [md['name'] for md in self.data.get('mds', [])]
        devices.extend(prt.get('name') for prt in self.partitions)
        return devices

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
                raise WrongPartitionSchemeError(
                    "Starting point on {0} partition is greater than the end "
                    "point.\nbegin({1}) > end({2})".format(partition['name'],
                                                           partition['begin'],
                                                           partition['end']))

    def validate_pvs(self):
        devices = self.get_all_devices()
        for pv in self.data.get('pvs', []):
            if pv['name'] not in devices:
                raise WrongPartitionSchemeError(
                    "Physical Volume cannot be assigned to non-existing "
                    "device.\n'{0}' not in {1}".format(pv['name'], devices))

    def validate_vgs(self):
        existing_pvs = set(pv['name'] for pv in self.data.get('pvs', []))
        for vg in self.data.get('vgs', []):
            for pvname in vg['pvnames']:
                if pvname not in existing_pvs:
                    raise WrongPartitionSchemeError(
                        "Volume Group is trying to use non-existing "
                        "Physical Volume.\n{0} not in {1}".format(pvname,
                                                                  existing_pvs)
                    )

    def validate_lvs(self):
        vg_names = set(vg['name'] for vg in self.data.get('vgs', []))
        for lv in self.data.get('lvs', []):
            if lv['vgname'] not in vg_names:
                raise WrongPartitionSchemeError(
                    "Logical Volume is trying to use non-existing "
                    "Volume Group.\n{0} not in {1}".format(lv['vgname'],
                                                           vg_names))

    def validate_fss(self):
        pass


class HumanReadableSchemeValidator(BaseValidator):

    SIMPLE_FORMAT_SCHEMA = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Volume Management Metadata',
        'type': 'object',
        'properties': {
            'pvs': {
                'title': 'Physical volumes',
                'type': 'array',
                'items': {
                    'title': 'Physical volume',
                    'type': 'object',
                    'properties': {
                        'id': {
                            'description': 'Index of physical volume',
                            'type': 'number'
                        },
                    },
                    '$ref': '#/definitions/deviceBySystemOrReference',
                    'required': ['id'],
                },
            },
            'vgs': {
                'title': 'Volume groups',
                'type': 'array',
                'items': {
                    'title': 'Volume group',
                    'type': 'object',
                    'properties': {
                        'id': {
                            'description': 'Index of volume group',
                            'type': 'number',
                        },
                        'name': {
                            'type': 'string'
                        },
                        'label': {
                            'type': 'string'
                        },
                        'pvs': {
                            'type': 'array',
                            'title': 'Physical volumes indices',
                            'items': {
                                'type': 'number'
                            }
                        }
                    },
                    'required': ['id', 'name', 'pvs', 'label']
                }
            },
            'lvs': {
                'title': 'Logical volumes',
                'type': 'array',
                'items': {
                    'title': 'Logical volume',
                    'type': 'object',
                    'properties': {
                        'id': {
                            'description': 'Index of logical volume',
                            'type': 'number',
                        },
                        'name': {
                            'type': 'string'
                        },
                        'vgname': {
                            'description': 'Volume group name',
                            'type': 'string'
                        },
                        'size': {
                            '$ref': '#/definitions/size',
                        }
                    },
                    'required': ['id', 'name', 'vgname', 'size']
                }
            },
            'mds': {
                'title': 'Multiple devices',
                'type': 'array',
                'items': {
                    'title': 'Multiple device',
                    'type': 'object',
                    'properties': {
                        'id': {
                            'description': 'Index of multiple device',
                            'type': 'number',
                        },
                        'devices': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                '$ref': '#/definitions/pathPattern'
                            }
                        },
                        'spares': {
                            'type': 'array',
                            'items': {
                                '$ref': '#/definitions/pathPattern'
                            }
                        },
                    },
                    'required': ['id', 'devices', 'spares']
                }
            },
            'parteds': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    '$ref': '#/definitions/deviceBySystemOrReference',
                    'properties': {
                        'id': {
                            'type': 'number',
                        },
                        'label': {
                            'type': 'string',
                        },
                        'name': {
                            'type': 'string',
                        },
                        'partitions': {
                            'title': 'Partitions',
                            'type': 'array',
                            'items': {
                                'title': 'Partition',
                                'type': 'object',
                                'required': ['id', 'begin', 'end',
                                             'partition_type'],
                                'properties': {
                                    'id': {
                                        'type': 'number',
                                    },
                                    'begin': {
                                        'type': 'number',
                                        'minimum': 1,
                                    },
                                    'end': {
                                        'type': 'number',
                                        'minimum': 2,
                                    },
                                    'name': {
                                        'type': 'string'
                                    },
                                    'count': {
                                        'type': 'number'
                                    },
                                    'partition_type': {
                                        'type': 'string',
                                    },
                                    'guid': {
                                        'type': 'string',
                                    },
                                },
                                '$ref': ('#/definitions/'
                                         'deviceBySystemOrReference'),
                            }
                        }
                    }
                }
            },
            'fss': {
                'title': 'File systems',
                'type': 'array',
                'items': {
                    'title': 'File system',
                    'type': 'object',
                    'required': ['id', 'mount', 'fs_type', 'fs_label'],
                    'allOf': [
                        {'properties': {
                            'id': {
                                'description': 'Index of filesystem',
                                'type': 'number',
                            },
                            'mount': {
                                '$ref': '#/definitions/pathPattern'
                            },
                            'fs_type': {
                                'type': 'string'
                            },
                            'fs_label': {
                                'type': 'string'
                            }
                        }},
                        {'$ref': '#/definitions/deviceBySystemOrReference'}
                    ]
                }
            }
        },
        'definitions': {
            'deviceBySystemOrReference': {
                'required': ['device'],
                'properties': {
                    'device': {
                        'description': 'Device metadata path',
                        '$ref': '#/definitions/devicePattern'
                    },
                }
            },
            'pathPattern': {
                'pattern': consts.PATH_REGEXP,
                'type': 'string'
            },
            'devicePattern': {
                'pattern': consts.DEVICE_REGEXP,
                'type': 'string',
            },
            'size': {
                "oneOf": [
                    {
                        'type': 'string',
                        'pattern': consts.HUMAN_READABLE_SIZE_REGEXP,
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'min': {
                                'type': 'number',
                            },
                            'best': {
                                'type': 'number',
                            },
                            'max': {
                                'type': 'number',
                            }
                        }
                    }
                ],
            }
        }
    }

    def validate(self, dict_scheme):
        self.validate_schema(dict_scheme)
        self.validate_device_existence_and_duplication(dict_scheme)
        self.validate_vg_pv_assignment(dict_scheme)
        self.validate_vg_existence_for_lvs(dict_scheme)
        self.validate_pv_double_usage(dict_scheme)

    def validate_schema(self, dict_scheme):
        try:
            checker = jsonschema.FormatChecker()
            jsonschema.validate(dict_scheme, self.SIMPLE_FORMAT_SCHEMA,
                                format_checker=checker)
        except Exception as exc:
            LOG.exception("Wrong partition scheme")
            raise WrongPartitionSchemeError(six.text_type(exc))

    def validate_device_existence_and_duplication(self, dict_scheme):
        all_objects = itertools.chain.from_iterable([y for _, y in
                                                     dict_scheme.iteritems()])
        for obj in (x for x in all_objects
                    if 'device' in x and x['device'][0] == '@'):
            splitted = obj['device'].split('/')
            key, ids = splitted[0], splitted[1:]
            key = key[1:]

            if key == 'parteds':
                matching_parteds = [x for x in dict_scheme[key]
                                    if int(x['id']) == int(ids[0])]
                if len(matching_parteds) != 1:
                    raise WrongPartitionSchemeError(
                        'Parted with id {0} does not exist'
                        ' or is duplicated'.format(ids[0]))
                parent = matching_parteds[0]['partitions']
                id = ids[1]
            else:
                parent = dict_scheme[key]
                id = ids[0]

            matching_devices = [
                x for x in parent if int(x['id']) == int(id)]
            if len(matching_devices) != 1:
                raise WrongPartitionSchemeError(
                    'Device {0} does not exist or is duplicated'.format(
                        obj['device'])
                )

    def validate_vg_pv_assignment(self, dict_scheme):
        pvs_ids = [x['id'] for x in dict_scheme['pvs']]
        for vg in dict_scheme['vgs']:
            if any([pv_id not in pvs_ids for pv_id in vg['pvs']]):
                raise WrongPartitionSchemeError(
                    'Volume group {0} consists of non-existent'
                    ' physical volumes'.format(vg['id']))

    def validate_pv_double_usage(self, dict_scheme):
        used_pvs_ids = itertools.chain.from_iterable([vg['pvs'] for vg in
                                                      dict_scheme['vgs']])
        pvs_frequencies = [(k, len(list(group))) for k, group in
                           itertools.groupby(sorted(used_pvs_ids))]
        if any(x[1] > 1 for x in pvs_frequencies):
            failed_pvs = [x for x in pvs_frequencies if x[1] > 1]
            raise WrongPartitionSchemeError(
                'Following pvs were used too many times: {0}'.format(
                    failed_pvs)
            )

    def validate_vg_existence_for_lvs(self, dict_scheme):
        vgs_names = [x['name'] for x in dict_scheme['vgs']]
        for lv in dict_scheme['lvs']:
            if lv['vgname'] not in vgs_names:
                raise WrongPartitionSchemeError(
                    ('Logical volume {0} tries to use non-existent volume'
                     ' group with name {1}').format(lv['id'], lv['vgname']))
