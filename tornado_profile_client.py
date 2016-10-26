#!/usr/bin/env python


import argparse
import datetime

import requests
import prettytable
import dns.resolver


def main():
    args = parse_args()
    servers = get_servers(args)
    print 'Will profile servers:'
    for server in servers:
        print '-', server
    print

    if args.action == 'status':
        docs = multi_request(servers, 'GET', 'profiler', json=True)
        print make_table(docs)
    elif args.action == 'start':
        docs = multi_request(servers, 'POST', 'profiler')
        print make_table(docs)
    elif args.action == 'stop':
        docs = multi_request(servers, 'DELETE', 'profiler')
        print make_table(docs)
    elif args.action == 'clear':
        docs = multi_request(servers, 'DELETE', 'profiler/stats')
        print make_table(docs)
    elif args.action == 'stats':
        _docs = multi_request(servers, 'GET', 'profiler/stats', json=True,
                              params={'sort': args.order, 'count': args.num,
                                      'strip_dirs': args.strip_dirs})
        docs = []
        for doc in _docs:
            if 'statistics' in doc:
                for item in doc.pop('statistics'):
                    item.update(doc)
                    docs.append(item)
            else:
                docs.append(doc)
        combined = {}

        def combine_stats(docs):
            errors = []
            for doc in docs:
                if 'error' in doc:
                    errors.append(doc)
                    continue
                key = (doc['path'], doc['line'], doc['func_name'])
                if key not in combined:
                    combined[key] = {'total_time': doc['total_time'],
                                     'cum_time': doc['cum_time'],
                                     'num_calls': doc['num_calls'],
                                     'path': doc['path'],
                                     'line': doc['line'],
                                     'func_name': doc['func_name']}
                else:
                    combined[key]['total_time'] += doc['total_time']
                    combined[key]['cum_time'] += doc['cum_time']
                    combined[key]['num_calls'] += doc['num_calls']
            for doc in combined.itervalues():
                calls = float(doc['num_calls'])
                doc['total_time_per_call'] = doc['total_time'] / calls
                doc['cum_time_per_call'] = doc['cum_time'] / calls

            if errors:
                print make_table(errors)
                print

            return combined.values()

        if not args.no_merge:
            docs = combine_stats(docs)
            if not docs:
                return

        for doc in docs:
            if 'error' in doc:
                continue
            for field in ('total_time', 'cum_time',
                          'total_time_per_call', 'cum_time_per_call'):
                doc[field] = datetime.timedelta(seconds=doc[field])
            doc['file'] = '%s:%s' % (doc.pop('path'), doc.pop('line'))

        table = make_table(docs, headers=('host', 'file', 'func_name',
                                          'num_calls', 'total_time',
                                          'cum_time', 'total_time_per_call',
                                          'cum_time_per_call'))
        if args.order in table.field_names:
            table.sortby = args.order
            table.reversesort = True
        for key in table.align:
            if key == 'num_calls':
                table.align[key] = 'r'
            else:
                table.align[key] = 'l'
        print table
    else:
        raise Exception("Invalid action: %s" % args.action)


def parse_args():
    """Define CLI argument parser and return arguments"""
    argparser = argparse.ArgumentParser(description="Profile SockJS-Tornado")

    # Parent parser with arguments common to all subparsers.
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('-p', '--port', type=int, default=80,
                        help="Default port to use to connect to servers.")
    parent.add_argument('-s', '--server', nargs='*',
                        help="Tornado server to profile.")
    parent.add_argument('-d', '--dns',
                        help=("Connect to all servers returned as A records "
                              "for this domain. Incompatible with -s option."))

    # Add action subparsers.
    subparsers = argparser.add_subparsers(dest='action')
    desc = "Get status of tornado profiler."
    subparsers.add_parser('status', parents=[parent],
                          description=desc, help=desc)
    desc = "Start tornado profiler."
    subparsers.add_parser('start', parents=[parent],
                          description=desc, help=desc)
    desc = "Stop tornado profiler."
    subparsers.add_parser('stop', parents=[parent],
                          description=desc, help=desc)
    desc = "Get tornado profiler stats."
    stats_parser = subparsers.add_parser('stats', parents=[parent],
                                         description=desc, help=desc)
    stats_parser.add_argument('-n', '--num', type=int, default=20,
                              help="Display this many top functions.")
    stats_parser.add_argument('-o', '--order', default='cum_time',
                              choices=('cum_time', 'total_time', 'num_calls',
                                       'cum_time_per_call',
                                       'total_time_per_call'),
                              help="Order entries based on this field.")
    stats_parser.add_argument('--strip-dirs', action='store_true',
                              help="Show only basename of functions & files.")
    stats_parser.add_argument('--no-merge', action='store_true',
                              help=("Don't merge profile results from "
                                    "multiple servers."))
    desc = "Clear tornado profiler stats."
    subparsers.add_parser('clear', parents=[parent],
                          description=desc, help=desc)

    # Parse arguments.
    args = argparser.parse_args()
    if args.dns and args.server:
        raise Exception("Can't define both `dns` and `server` options.")
    return args


def get_servers(args):
    """Get list of tornado hosts to profile from args"""
    if args.dns:
        servers = [record.address
                   for record in dns.resolver.query(args.dns, 'A')]
    else:
        servers = args.server or ['localhost']
    if args.port != 80:
        for i, server in enumerate(servers):
            if ':' not in server:
                servers[i] = '%s:%d' % (server, args.port)
    for i, server in enumerate(servers):
        if not (server.startswith('http://') or server.startswith('https://')):
            servers[i] = 'http://%s' % server
    return servers


def request(host, method, path, params=None, json=False):
    """Perform request with proper error handling and consistent response"""
    print "%s %s/%s ..." % (method, host, path)
    try:
        resp = requests.request(method, '%s/%s' % (host, path), params=params)
    except Exception as exc:
        return {"error": repr(exc)}
    if not resp.ok:
        return {"error": "%d: %s" % (resp.status_code, resp.text[:200])}
    if json:
        try:
            return resp.json()
        except Exception as exc:
            return {"error": "Parsing json on '%s': %r" % (resp.text, exc)}
    if resp.text.strip():
        return {"response": resp.text.strip()}
    return {"response": "OK"}


def multi_request(hosts, method, path, params=None, json=False):
    """Perform request on multiple hosts"""
    docs = []
    for host in hosts:
        doc = request(host, method, path, params=params, json=json)
        doc['host'] = host
        docs.append(doc)
    print
    return docs


def make_table(docs, headers=('host', )):
    # Find columns
    keys = set()
    for doc in docs:
        keys.update(doc.keys())
    columns = []
    if headers is not None:
        for header in headers:
            if header in keys:
                keys.remove(header)
                columns.append(header)
    for key in sorted(keys):
        if key != 'error':
            keys.remove(key)
            columns.append(key)
    for key in keys:
        columns.append(key)
    # Construct table
    table = prettytable.PrettyTable(columns)
    for doc in docs:
        table.add_row([doc.get(col, '') for col in columns])
    # Set max widths
    for key in ('error', 'response'):
        if key in columns:
            table.max_width[key] = 100
    print table.fields
    return table


if __name__ == '__main__':
    main()
