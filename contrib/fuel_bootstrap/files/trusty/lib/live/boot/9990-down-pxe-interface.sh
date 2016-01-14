#!/bin/sh

# The ethernet interface used for PXE boot is up now.
# In case of using predictable interface naming
# schema, udev will attempt to rename the interface
# (later on Upstart phase), but receive "device busy", 
# due to the interface is in UP state.
# Put the interface down allowing udev to rename it.
# Look throw the interfaces 

#set -e

Down_pxe_interface()
{
  IFFILE="/root/etc/network/interfaces"

   for device in /sys/class/net/*
   do
       interface=${device##*/}
       if [ "$pxe_interface" != "lo" ]; 
       then
          if [ -f "$device/operstate" ] && [  $(cat "$device/operstate") = "up" ];
          then
               ifconfig "$interface" down
               # Make the interface auto allow it being made up on bootstrap
               if [ -e $IFFILE ];
               then
                  sed -ie "/allow-hotplug ${interface}/ i auto ${interface}" $IFFILE
               fi
               break
          fi
       fi
   done
}
