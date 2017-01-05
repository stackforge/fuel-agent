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

from cliff import lister

from fuelclient.common import data_utils

from fuel_bootstrap.commands import base
from fuel_bootstrap.utils import bootstrap_image as bs_image


class ListCommand(base.BaseCommand, lister.Lister):
    """List all available bootstrap images."""

    columns = ('uuid', 'label', 'status')

    def take_action(self, parsed_args):
        super(ListCommand, self).take_action(parsed_args)
        data = bs_image.get_all()
        data = data_utils.get_display_data_multi(self.columns, data)
        return (self.columns, data)
