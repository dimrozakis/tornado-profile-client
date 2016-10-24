tornado-profile-client
======================

This is a python script to interface with [tornado-profile](https://github.com/makearl/tornado-profile).

It is a standalone script `tornado_profile_client.py`, and if installed it will
come up as `tornado-profile-client` in the PATH.

It can be used to start and stop the profiler on a tornado server, as well as
fetch and clear stats.

The script can run all commands on multiple servers. When fetching data, the
stats will by default be merged.

All results are displayed into pretty tables.

To get information on the available options, use `tornado-profile-client -h` or
`tornado-profile-client <action> -h`.

When runnning the script on multiple servers, one can either define a list of
servers to run the script on, or use the `--dns` entry. This will query the DNS
name and run the script on all A records returned for that domain. This is
useful when running multiple tornado instances behind round robin DNS, when
running multiple tornado instances in a kubernetes cluster with a headless
service, etc.
