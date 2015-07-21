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
