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

from fuel_bootstrap import settings

CONF = settings.Configuration()


class SetSettingsCommand(command.Command):
    """Configure fuel bootstrap settings.

       ***WARNING*** Please note that with custom attributes some commands
       may not work propperly
    """

    def get_parser(self, prog_name):
        parser = super(SetSettingsCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--name',
            type=str,
            metavar='ATTR_NAME',
            help="Name of attribute"
        )
        parser.add_argument(
            '--value',
            type=str,
            metavar='VALUE',
            help="New value of selected attribute"
        )
        parser.add_argument(
            '--load-default',
            help="Return default settings",
            action='store_true'
        )
        return parser

    def take_action(self, parsed_args):
        if parsed_args.load_default:
            CONF.load_default()
            self.app.stdout.write("Default settings was loaded\n")
        else:
            CONF.update_attribute(parsed_args.name,
                                  parsed_args.value)
            self.app.stdout.write("Attribute has been updated\n")


class ShowSettingsCommand(command.Command):
    """Show fuel bootstrap settings"""

    def get_parser(self, prog_name):
        parser = super(ShowSettingsCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--name',
            type=str,
            metavar='ATTR_NAME',
            help="Name of attribute to be shown"
        )
        parser.add_argument(
            '--all',
            help="Show all configurations",
            action='store_true'
        )
        return parser

    def take_action(self, parsed_args):
        if parsed_args.all:
            value = "\n".join(CONF.get_all())
        else:
            value = getattr(CONF, parsed_args.name)
            if value is None:
                value = "No such attribute"
        self.app.stdout.write(value + "\n")
