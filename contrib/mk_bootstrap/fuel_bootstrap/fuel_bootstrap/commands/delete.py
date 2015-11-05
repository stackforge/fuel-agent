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

from cliff import command

from fuel_bootstrap.utils import bootstrap_image as bs_image


class DeleteCommand(command.Command):
    """Delete specified bootstrap image from the system."""

    def get_parser(self, prog_name):
        parser = super(DeleteCommand, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            type=str,
            metavar='ID',
            help='ID of bootstrap image to be deleted')
        return parser

    def take_action(self, parsed_args):
        bs_image.delete(parsed_args.id)
        self.app.stdout.write('Bootstrap image with ID={0} was deleted '
                              'successfuly.\n'.format(parsed_args.id))
