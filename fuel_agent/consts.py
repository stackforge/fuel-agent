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

# TODO(sbrzeczkowski) move all constants here


PATH_REGEXP = r'^((/)|((/[^/]+)+))$'

DEVICE_REGEXP = (r'^((@(lvs|parteds|mds)(/[1-9][0-9]*)+)|%s)$'
                 % PATH_REGEXP[1:-1])

HUMAN_READABLE_SIZE_REGEXP = (r'^(?:\d+([,.]\d+)?){1} ?(?:[BkKMGTPEZY]'
                              '(?:i|B|iB)?|(byte|bytes|mega|giga|tera|peta'
                              '|exa|zetta|yotta|kibi|mebi|gibi|tebi|pebi'
                              '|exbi|zebi|yobi){1})?$')
