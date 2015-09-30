Fuel Agent driver for Ironic
============================

Fuel Agent driver adds possibility to use Fuel Agent as deploy agent
for Ironic.

Important note for package maintainers: because ironic-fa-deploy does not
have own git repository you must set "PBR_VERSION" variable or include
egg-info in the tarball, reference:
http://docs.openstack.org/developer/pbr/packagers.html
