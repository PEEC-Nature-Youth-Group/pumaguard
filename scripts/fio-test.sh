#!/bin/bash

fio --name=sd_random \
    --directory /run/media/nbock/writable/tmp/ \
    --size=512M \
    --rw=randrw \
    --rwmixread=70 \
    --bs=4K \
    --ioengine=libaio \
    --direct=1 \
    --iodepth=4 \
    --runtime=30 \
    --time_based \
    --group_reporting
