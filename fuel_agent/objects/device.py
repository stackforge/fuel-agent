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

from fuel_agent import errors
from fuel_agent.utils import build as bu


class Loop(object):
    def __init__(self, name=None, attached=False):
        self.name = name
        self.attached = False

    def attach_file(self, filename):
        bu.attach_file_to_loop(filename, str(self))
        self.attached = True

    def deattach_file(self, check_exit_code=[0]):
        bu.deattach_loop(str(self), check_exit_code)
        self.attached = False

    def is_attached(self):
        return self.attached

    def __str__(self):
        if self.name:
            return self.name
        raise errors.WrongDeviceError(
            'Loop device can not be stringified. '
            'Name attribute is not set. Current: '
            'name={0}'.format(self.name))
