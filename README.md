fuel-agent README
=================

## Table of Contents

1. [Overview - What is the fuel-agent?](#overview)
2. [Structure - What is in the fuel-agent?](#structure)
3. [Official documention](#docs)
4. [Development](#development)
5. [How to use fuel-agent with Ironic](#fuel-agent-with-ironic)
6. [How to use fuel-agent with pure Ironic(no Nailgun/ other Fuel parts)](#fuel-agent-wo-fuel)
7. [How to deploy fuel-agent](#deploy)
8. [Core Reviewers](#core-reviewers)
9. [Contributors](#contributors)

## Overview
-----------

fuel-agent is nothing more than just a set of data driven executable
scripts.
- One of these scripts is used for building operating system images and we run
this script on the master node passing a set of repository URIs and a set of
package names to it.
- Another script is used for the actual provisioning. We run it on each node
and pass provisioning data to it. These data contain information about disk
partitions, initial node configuration, operating system image location, etc.
So, this script being run on a node, prepares disk partitions, downloads
operating system images and puts these images on partitions.


## Structure
------------

### Basic Repository Layout

```
fuel-agent
├── cloud-init-templates
├── debian
├── etc
├── fuel_agent
│   ├── cmd
│   ├── drivers
│   ├── objects
│   ├── openstack
│   ├── tests
│   ├── utils
├── openstack-common.conf
├── README.md
├── LICENSE
├── requirements.txt
├── run_tests.sh
├── setup.cfg
├── setup.py
├── specs
├── test-requirements.txt
```

### root

The root level contains important repository documentation and license information.
It also contais files which are typical for the infracture of python project such
as requirements.txt and setup.py

### cloud-init-templates

This folder contains Jinja2 templates to prepare [cloud-init](https://cloudinit.readthedocs.org/en/latest/) related data for [nocloud](http://cloudinit.readthedocs.org/en/latest/topics/datasources.html#no-cloud) [datasource](http://cloudinit.readthedocs.org/en/latest/topics/datasources.html#what-is-a-datasource).

### debian

This folder contains the required information to create fuel-agent debian package.
Included debian rules are mainly suitable for Ubuntu 12.04 or higher.

### etc

This folder contains the sample config file for fuel-agent. Every parameter is well documented.

### fuel_agent

This folder contains the python code: drivers, objects, unit tests and utils

### spec

This folder contains the rpm spec file for fuel-agent rpm packages.
Included RPM spec is mainly suitable for Centos 6.x or higher.


## Docs
-------

Links to official Fuel documentation:

* [Image based provisionig](https://docs.mirantis.com/openstack/fuel/fuel-master/reference-architecture.html#image-based-provisioning)
* [Fuel Agent](https://docs.mirantis.com/openstack/fuel/fuel-master/reference-architecture.html#fuel-agent)
* [Operating system provisioning](https://docs.mirantis.com/openstack/fuel/fuel-master/reference-architecture.html#operating-system-provisioning)
* [Image building](https://docs.mirantis.com/openstack/fuel/fuel-master/reference-architecture.html#image-building)


## Development
--------------
            
* [Fuel Development Documentation](https://docs.fuel-infra.org/fuel-dev/)
* [Fuel How to Contribute](https://wiki.openstack.org/wiki/Fuel/How_to_contribute)


## fuel-agent with Ironic
-------------------------

TODO


## fuel-agent without Fuel
--------------------------

TODO


## Deploy
---------

Fuel Agent could be packaged to both RPM or DEB package.
Later, this package could be installed into PXE bootable ramdisk image.

TODO


## Core Reviewers
-----------------

* [Fuel Agent Cores](https://review.openstack.org/#/admin/groups/995,members)


## Contributors
---------------

* [Stackalytics](http://stackalytics.com/?release=all&project_type=all&module=fuel-agent&metric=commits)
