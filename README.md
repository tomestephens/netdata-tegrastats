
Simple package to display all of the core data from Tegrastats into Netdata (https://my-netdata.io).
It took me a little while to understand netdata enough to make these charts so I figure I can save someone the trouble.

Also including a super simple service def for running tegrastats to a logfile so this collector can pull that data and parse it for netdata.

I built all of this for development purposes, not sure I would run any of this on a production machine without some extra work/benchmarking.

Destination directories for this to work:

netdata/netdata.conf        ->  /etc/netdata/netdata.conf
netdata/python.d.conf       ->  /etc/netdata/python.d.conf
netdata/tegrastats.conf     ->  /etc/netdata/python.d/tegrastats.conf
netdata/tegrastats.chart.py ->  /usr/libexec/netdata/python.d/tegrastats.chart.py

service/tegrastats.service  ->  /etc/systemd/system/tegrastats.service
service/run_tegrastats.sh   ->  /etc/run_tegrastats.sh

I have run this successfully using the netdata/netdata docker container as well, just built a script that copied all of this to the right location before starting running the default entrypoint. You'd also need to make the tegrastats.log available in a volume and update tegrastats.conf appropriately.

Also want to call out that I really just took the parsing from https://github.com/rbonghi/jetson_stats and applied it to a netdata format.
