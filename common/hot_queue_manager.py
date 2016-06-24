#! /usr/bin/env python
# coding: utf-8

import sys
import click
import json
from hot_url_queue import HotUrlQueue

def dump_tasks(tasks, dump_f):
    for t in tasks:
        tmp = json.loads(t[0])
        tmp['params']['hot'] = t[1]
        dump_f.write(json.dumps(tmp) + '\n')


def load_tasks(load_f):
    for t in load_f:
        j_t = json.loads(t)
        hot = j_t['params'].pop('hot')
        yield json.dumps(j_t), hot


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version 1.0')
    ctx.exit()


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.option('--address', '-a', default='redis://127.0.0.1:6379/0', help='redis url format:"redis://host:port/db"')
@click.option('--hot_key', '-k', default='hot', help='the hot key name, default is "hot"')
@click.pass_context
def cli(ctx, address, hot_key):
    '''
    hot url queue manager implementation using redis
    '''
    if ctx.invoked_subcommand is None:
        click.echo('no subcommand')
        click.echo(address)
        click.echo(hot_key)
        #huq = HotUrlQueue(hot_key=hot_key, url=address)
    else:
        ctx.obj['ADDRESS'] = address
        ctx.obj['HOT_KEY'] = hot_key


@cli.command(short_help='dump tasks from hot url queue')
@click.option('--hot_range', '-r', type=int, nargs=2, help='hot range to dump')
@click.option('--hot_value', '-v', default=0, type=int, help='hot value to dump, ignore hot_range option')
@click.option('--count', '-c', type=int, default=0, help='count of task to dump, ignore hot_value and hot_range options')
@click.option('--lowest', '-l', is_flag=True, default=False, help='the flag of dumping lowest hot task, default is highest')
@click.option('--delete', '-d', is_flag=True, default=False, help='the flag of deleting dumped tasks from hot url queue, default is undeleted')
@click.argument('dump_file', type=click.File('w'))
@click.pass_context
def dump(ctx, hot_range, hot_value, count, lowest, dump_file, delete):
    '''
    dump some tasks to disk from hot_url_queue and delete the tasks from queue
    address format: redis://host:port/db
    dump_file: should can be writed, task will be saved in it. format: json rpc string 
    if no any options, dump all data
    '''
    try:
        click.echo('Start dump tasks from hot url queue....')
        hot_key, address = ctx.obj['HOT_KEY'], ctx.obj['ADDRESS']
        tasks = []
        huq = HotUrlQueue(hot_key=hot_key, url=address)
        if count > 0:
            if lowest:
                print "dump lowest hot urls, count is %d" % count
                tasks = huq.get_lowest_hots(count, withhots=True)
            else:
                print "dump higest hot urls, count is %d" % count
                tasks = huq.get_highest_hots(count, withhots=True)
        elif hot_value > 0:
            print "dump urls, hot is %d" % hot_value
            tasks = huq.get_url_tasks_by_hot(
                hot_value, hot_value, withhots=True)
        elif hot_range:
            print "dump urls, hot range is [%d -- %d]" % hot_range
            tasks = huq.get_url_tasks_by_hot(
                hot_range[0], hot_range[1], withhots=True)

        else:
            print "dump all urls"
            size = huq.get_size()
            tasks = huq.get_highest_hots(size, withhots=True)

        if not tasks:
            print "no any task to dump"

        dump_tasks(tasks, dump_file)
        if delete:
            print 'remove tasks has dumped'
            huq.remove_by_urls(*[t[0] for t in tasks])
        print "dump success, dump file is %s" % dump_file
    except:
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command(short_help='load tasks into hot url queue')
@click.argument('load_file', type=click.File('r'))
@click.option('--reset_hot', '-r', is_flag=True, default=False, help='if task in queue, reset the hot value, default increase the hot value')
@click.pass_context
def load(ctx, load_file, reset_hot):
    '''
    load tasks into hot url queue
    '''
    try:
        click.echo('start load tasks into hot url queue....')
        hot_key = ctx.obj['HOT_KEY']
        address = ctx.obj['ADDRESS']
        huq = HotUrlQueue(hot_key=hot_key, url=address)
        if load_file:
            tasks = load_tasks(load_file)
            for task, hot in tasks:
                try:
                    if not reset_hot:
                        huq.incr_hot(task, hot)
                    else:
                        huq.set_hot(task, hot)
                except Exception, err:
                    print >> sys.stderr, 'load error, task is %s, reason:%s' % (
                        task, err)
        print 'load tasks successfully'
    except:
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command(short_help='show hot url queue')
@click.option('--highest', '-h', is_flag=True, default=False, help='show highest hot and count')
@click.option('--lowest', '-l', is_flag=True, default=False, help='show lowest hot and count')
@click.option('--hot_value', '-v', type=int, default=0, help='show the count of tasks with hot value')
@click.option('--hot_range', '-r', nargs=2, type=int, help='show the count of tasks with hot range')
@click.pass_context
def show(ctx, highest, lowest, hot_value, hot_range):
    '''
    show hot url queue infos: quque_size, used_memory, max_memory
    '''
    try:
        hot_key = ctx.obj['HOT_KEY']
        address = ctx.obj['ADDRESS']
        click.echo('show hot url queue info')
        huq = HotUrlQueue(hot_key=hot_key, url=address)
        print 'queue size is %d' % huq.get_size()
        print 'used_memory is %d' % huq.get_used_memory()
        print 'max_memory is %d' % huq.get_max_memory()
        if highest:
            tasks = huq.get_highest_hots(1, withhots=True)
            highest_hot = tasks[0][1]
            highest_cnt = len(
                huq.get_url_tasks_by_hot(highest_hot, highest_hot))
            print 'highest hot is %d, count is %d' % (highest_hot, highest_cnt)
        if lowest:
            tasks = huq.get_lowest_hots(1, withhots=True)
            lowest_hot = tasks[0][1]
            lowest_cnt = len(huq.get_url_tasks_by_hot(lowest_hot, lowest_hot))
            print 'lowest hot is %d, count is %d' % (lowest_hot, lowest_cnt)
        if hot_value > 0:
            hot_cnt = len(huq.get_url_tasks_by_hot(hot_value, hot_value))
            print '[%d] hot count: %d' % (hot_value, hot_cnt)
        if hot_range:
            hot_cnt = len(huq.get_url_tasks_by_hot(hot_range[0], hot_range[1]))
            print '[%d -- %d] hot count: %d' % (hot_range[0], hot_range[1], hot_cnt)

    except:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    cli(obj={})
