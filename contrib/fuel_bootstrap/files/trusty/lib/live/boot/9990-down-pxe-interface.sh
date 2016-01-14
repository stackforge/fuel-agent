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
   for device in /sys/class/net/*
   do
       interface=${device##*/}
       if [ "$pxe_interface" != "lo" ]; 
       then
          if [ -f "$device/operstate" ] && [  $(cat "$device/operstate") = "up" ];
          then
               ifconfig "$interface" down
               break
          fi
       fi
   done
}
