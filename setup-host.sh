#!/bin/bash

# Set all CPU cores to use the 'performance' frequency governor
sudo cpupower frequency-set --governor performance

# Disable Hyper-Threading
echo off | sudo tee /sys/devices/system/cpu/smt/control

# Disable Address Space Layout Randomization (ASLR)
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space

# Disable real-time scheduler runtime limits
echo -1 | sudo tee /proc/sys/kernel/sched_rt_runtime_us
