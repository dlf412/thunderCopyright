#coding: utf-8

import os
import sys
import json
import commands
import ConfigParser


def supervisor(CONFIG_PATH):
    
    def parse_programs(supervisor_path):
        parser = ConfigParser.RawConfigParser()
        parser.read(supervisor_path)
    
        def get_programs(cfg):
            lst = []
            for section in cfg.sections():
                if section.startswith('program:'):
                    lst.append(section.split(':')[1])
            return lst
    
        def parse_include(path, files):
            lst = []
            cmd = 'cd %s && ls %s' % (path, files)
            output = commands.getoutput(cmd)
            for sub_name in output.split('\n'):
                sub_path = os.path.join(path, sub_name)
                sub_parser = ConfigParser.RawConfigParser()
                sub_parser.read(sub_path)
                lst.extend(get_programs(sub_parser))
            return lst
    
        programs = get_programs(parser)
        try:
            files = parser.get('include', 'files')
            s_path, s_name = os.path.split(supervisor_path)
            programs.extend(parse_include(s_path, files))
        except ConfigParser.NoSectionError:
            pass
    
        return programs
    
    
    VALID_PROGS = parse_programs(os.path.join(os.environ['PWD'], CONFIG_PATH))
    VALID_PROGS.append('all')
    
    USAGE = '''
      Usage: ./bin/server {boot|start|restart|stop|status|tail|shutdown} [program]
      ----------------------------------------------------------------------------
        help                -->  Print this then exit.
        boot                -->  Start supervisord and start all programs
        start   [program]   -->  Start a program, or start all program
        restart [program]   -->  Restart a program, or restart all program
        stop    [program]   -->  Stop a program, or stop all program
        status              -->  Show statuses of all programs
        tail    [program]   -->  Show log of a program
        shutdown            -->  Stop all programs then stop supervisor
    
      { Enabled programs } :  %(programs)s
        ''' % {'programs': json.dumps(VALID_PROGS)}
    
    
    # ==============================================================================
    #  Main functions
    # ==============================================================================
    def execute(cmd):
        # print 'Execute: [ %s ]' % cmd
        # print '-' * 60
        output = commands.getoutput(cmd)
        print output
        return output
    
    
    def invoke(action, arg):
        arg = '' if arg is None else arg
        cmd = 'supervisorctl -c %s %s %s' % (CONFIG_PATH, action, arg)
        return execute(cmd)
    
    
    def check_arg_required(name, arg):
        if arg not in VALID_PROGS:
            print >> sys.stderr, 'Argument not found: %r !' % arg
            print >> sys.stderr, 'Valid program: %r' % (VALID_PROGS, )
            if name == 'start':
                print >> sys.stderr, '\n    Use [ ./bin/server boot ] to start supervisor !'
                print >> sys.stderr, '    Use [ ./bin/server help ] to see details !'
            sys.exit(-1)
    
    
    def boot(arg):
        cmd = 'supervisord -c %s' % CONFIG_PATH
        execute(cmd)
        status(None)
        
    
    def mk_control_global(name):
        def control(arg):
            invoke(name, arg)
        return control
    
    def mk_control_prog(name):
        def control(arg):
            check_arg_required(name, arg)
            invoke(name, arg)
        return control
    
    globals()['boot'] = boot
    for name in ('shutdown', 'status'):
        globals()[name] = mk_control_global(name)
        
    for name in ('start', 'restart', 'stop', 'tail'):
        globals()[name] = mk_control_prog(name)
    
    
    def main():
        if len(sys.argv) < 2:
            print >> sys.stderr, 'Argument not enough!', sys.argv 
            print USAGE
            sys.exit(-1)
    
        cmd = sys.argv[1]
    
        if cmd == 'help':
            print USAGE 
            sys.exit(-1)
        
        cmds = ('boot', 'start', 'restart', 'stop', 'status', 'tail', 'shutdown')
        if cmd not in cmds:
            print >> sys.stderr, 'Command error:', cmd
            print >> sys.stderr, 'Valid command: %r' % (cmds,)
            sys.exit(-1)
    
        arg = None if len(sys.argv) < 3 else sys.argv[2]
        globals()[cmd](arg)
        print '-------'
        print '>> OK!'
        
    main()
