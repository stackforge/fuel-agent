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

import os
import yaml

from fuel_bootstrap import errors

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "configuration.yaml")
CUSTOM_CONFIG = os.path.join(os.path.dirname(__file__),
                             "custom_configuration.yaml")


class Configuration(object):
    def __init__(self):
        if os.path.exists(CUSTOM_CONFIG):
            with open(CUSTOM_CONFIG) as f:
                data = yaml.load(f)
        elif os.path.exists(DEFAULT_CONFIG):
            with open(DEFAULT_CONFIG) as f:
                data = yaml.load(f)
        else:
            raise errors.ConfigFileNotExists(
                "Default config couldn't be found in {0}"
                .format(os.path.abspath(DEFAULT_CONFIG)))
        self._data = data

    def _save(self):
        with open(CUSTOM_CONFIG, 'w') as f:
            f.write(yaml.dump(self._data))

    def __getattr__(self, name):
        return self._data.get(name)

    def update_attribute(self, name, value):
        self._data[name] = value
        self._save()

    def get_all(self):
        return ["{0}={1}".format(k, v) for k, v in self._data.iteritems()]

    def load_default(self):
        if os.path.exists(CUSTOM_CONFIG):
            os.remove(CUSTOM_CONFIG)
