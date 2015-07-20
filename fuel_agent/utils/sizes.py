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

import re

from fuel_agent.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class DehumanizeSize(object):
    int_float_pattern = r"(\d+(\.\d+)?)"

    def __init__(self, mapping):
        self.mapping = {}
        for keys, value in mapping:
            for key in keys:
                self.mapping[key] = value

    def __getitem__(self, key):
        return self._to_bytes(key)

    def _to_bytes(self, hvalue):
        "Return number of bytes (floored) as an integer."
        _, value, _, unit = re.split(self.int_float_pattern, hvalue)
        unit = unit.strip()
        if unit not in self.mapping:
            error = KeyError(
                '"{0}" unit is not supported. Use one of: {1}'.format(
                    unit, ', '.join(sorted(self.mapping.keys()))))

            LOG.exception(error)
            raise error

        return int(float(value) * self.mapping[unit])

SIZES = DehumanizeSize(
    (
        (('B', 'byte', 'Bi'), 1),
        (('K', 'kB', 'kilo'), 1000),
        (('M', 'MB', 'mega'), 1000**2),
        (('G', 'GB', 'giga'), 1000**3),
        (('T', 'TB', 'tera'), 1000**4),
        (('P', 'PB', 'peta'), 1000**5),
        (('E', 'EB', 'exa'), 1000**6),
        (('Z', 'ZB', 'zetta'), 1000**7),
        (('Y', 'YB', 'yotta'), 1000**8),

        (('Ki', 'kibi'), 1024),
        (('Mi', 'mebi'), 1024**2),
        (('Gi', 'gibi'), 1024**3),
        (('Ti', 'tebi'), 1024**4),
        (('Pi', 'pebi'), 1024**5),
        (('Ei', 'exbi'), 1024**6),
        (('Zi', 'zebi'), 1024**7),
        (('Yi', 'yobi'), 1024**8),
    )
)
