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


class BuildCommand(command.Command):
    """ Build new bootstrap image with specified parameters.
    """

    def get_parser(self, prog_name):
        parser = super(BuildCommand, self).get_parser(prog_name)
        # TODO: add possibility to read all options from file
        parser.add_argument(
                "--ubuntu-repository",
                type=str,
                metavar='REPOSITORY',
                help="Use the specified Ubuntu repository.",
                required=True
        )
        parser.add_argument(
                "--http-proxy",
                type=str,
                metavar='URL',
                help="Pass http-proxy URL."
        )
        parser.add_argument(
                '--https-proxy',
                type=str,
                metavar='URL',
                help="Pass https-proxy URL."
        )
        parser.add_argument(
                '--direct-repository',
                metavar='ADDR',
                help='########################TBA',
                action='append'
        )
        parser.add_argument(
                '--mos-repository',
                type=str,
                metavar='REPOSITORY',
                help="Add link to repository with fuel* packages. That "
                     "should either http://mirror.fuel-infra.org/mos-repos"
                     " or its mirror.",
                required=True
        )
        parser.add_argument(
                '--repository',
                dest='repositories',
                type=str,
                metavar='REPOSITORY',
                help="Add one more repository.",
                action='append'
        )
        parser.add_argument(
                '--script',
                dest='post_script_file',
                type=str,
                metavar='SCRIPT',
                help="The script is executed after installing package (both "
                     "mandatory and user specified ones) and before creating "
                     "initramfs. Also, it is possible to land into chroot "
                     "system and made any custom changes with '--script=/bin"
                     "/bash' command."
        )
        parser.add_argument(
                '--include-kernel-module',
                help="Make sure the given modules are included into initramfs "
                     "image. (by adding module into /etc/initramfs-tools/"
                     "modules) **NOTE** If the module in question is not "
                     "shipped with the kernel itself please add the package "
                     "providing it (see the `--packege` option). Keep in mind "
                     "that initramfs image should be kept as small as possible"
                     ". This option is intended to include uncommon network "
                     "interface cards' drivers so the initramfs can fetch the "
                     "root filesystem image via the network."

        )
        parser.add_argument(
                '--package',
                dest='packages',
                type=str,
                metavar='PKGNAME',
                help="The option can be given multiple times, all specified "
                     "packages and their dependencies will be installed.",
                action='append'
        )
        parser.add_argument(
                '--package-list-file',
                type=str,
                metavar='FILE_PATH',
                help="Install list of packages. Package names listed in the "
                     "given file."
        )
        parser.add_argument(
                '--label',
                type=str,
                metavar='LABEL',
                help="Custom string, which will be presented in bootstrap "
                     "listing."
        )
        parser.add_argument(
                '--blacklist-kernel-module',
                help="Make sure the given modules never get loaded "
                     "automatically. **NOTE** Direct injection of files into "
                     "the image is not recommended, and a proper way to "
                     "customize an image is adding (custom) packages."
        )
        parser.add_argument(
                '--inject-files-from',
                type=str,
                metavar='PATH',
                help="Directory or archive that will be injected to the image "
                     "root filesystem. **NOTE** Files/packages will be "
                     "injected after installing all packages, but before "
                     "generating system initramfs - thus it's possible to "
                     "adjust initramfs."
        )
        parser.add_argument(
                '--kernel-params',
                type=str,
                metavar='PARAMS',
                help="Custom kernel parameters"
        )
        parser.add_argument(
                '--kernel-flavor',
                type=str,
                help="Defines kernel version (default=-generic-lts-trusty)"
        )
        parser.add_argument(
                '--ubuntu-release',
                type=str,
                help="Defines the Ubuntu release (default=trusty)"
        )
        parser.add_argument(
                '--ssh-keys',
                type=str,
                metavar='FILE',
                help="Copy publick ssh key into image - makes it possible"
                     " to login as root into any bootstrap node using the"
                     " key in question"
        )
        parser.add_argument(
                'filename',
                type=str,
                metavar='ARCHIVE_FILE',
                help="Name of destination archive file"
        )
        return parser

    def take_action(self, parsed_args):
        bs_image.make_bootstrap(parsed_args)
        self.app.stdout.write("Seems all is good")
