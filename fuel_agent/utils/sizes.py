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

from decimal import Decimal
import re


class DehumanizeSize(object):
    int_float_pattern = re.compile(r"(\d+(\.\d+)?)")

    def __init__(self, mapping):
        self.mapping = {}
        for keys, value in mapping:
            for key in keys:
                self.mapping[key] = value

    def __getitem__(self, hvalue):
        "Returns number of bytes (floored)"
        try:
            _, value, _, unit = self.int_float_pattern.split(hvalue)
        except ValueError:
            raise KeyError("Unit without a value has been given")

        unit = unit.strip()
        if unit not in self.mapping:
            raise KeyError(
                '"{0}" unit (in "{1}") is not supported. '
                'Use one of: {2}'.format(
                    unit, hvalue, ', '.join(sorted(self.mapping.keys()))))

        return int(Decimal(value) * self.mapping[unit])

SIZES = DehumanizeSize(
    (
        (('B', 'byte', 'bytes', ''), 1),  # empty unit returns bytes as well
        (('kB', 'kilo'), 1000),
        (('MB', 'mega'), 1000**2),
        (('GB', 'giga'), 1000**3),
        (('TB', 'tera'), 1000**4),
        (('PB', 'peta'), 1000**5),
        (('EB', 'exa'), 1000**6),
        (('ZB', 'zetta'), 1000**7),
        (('YB', 'yotta'), 1000**8),

        (('Ki', 'K', 'KiB', 'kibi'), 1024),
        (('Mi', 'M', 'MiB', 'mebi'), 1024**2),
        (('Gi', 'G', 'GiB', 'gibi'), 1024**3),
        (('Ti', 'T', 'TiB', 'tebi'), 1024**4),
        (('Pi', 'P', 'PiB', 'pebi'), 1024**5),
        (('Ei', 'E', 'EiB', 'exbi'), 1024**6),
        (('Zi', 'Z', 'ZiB', 'zebi'), 1024**7),
        (('Yi', 'Y', 'YiB', 'yobi'), 1024**8),
    )
)
