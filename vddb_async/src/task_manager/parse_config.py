import re
from sys import stderr

config_parser = re.compile(
    "^[ \t]*([a-z0-9_]+)[ \t]*=[ \t]*([^#\n]+)[ \t]*(#.*)?$",
    re.IGNORECASE)


def parse_config(cf):
    try:
        config = {}
        with open(cf) as f:
            for l in f:
                mg = config_parser.match(l)
                if mg != None:
                    config[mg.group(1)] = mg.group(2).rstrip(" \t").strip("\"")
        return config
    except IOError as e:
        stderr.write("failed to read config file %s: (%s) %s" % (cf, e.errno,
                                                                 e.strerror))
        raise
