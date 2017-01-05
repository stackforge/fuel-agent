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

from fuel_bootstrap import consts
from fuel_bootstrap import settings

CONF = settings.CONF


class BaseCommand(command.Command):

    def get_parser(self, prog_name):
        parser = super(BaseCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--config',
            dest='config_file',
            type=str,
            metavar='FILE',
            default=consts.CONFIG_FILE,
            help="The config file is to be used for taking configuration"
                 " parameters from during building of the bootstrap."
        )
        return parser

    def take_action(self, parsed_args):
        CONF.read(parsed_args.config_file)
