usage of mylogger.py:
1. NEED to create 3 instances of class mylogger with different facility
2. using instance with facility LOG_LOCAL0 when logging some import or billing log
3. using instance with facility LOG_LOCAL1 when logging system debug info
4. using instance with facility LOG_LOCAL2 when logging other info like sql or very long infomation

====create instance of mylogger with a specified facility====
from mylogger import mylogger
from logging.handlers import SysLogHandler

g_logger_0 = mylogger()
g_logger_0.init_logger('CAS', 'LOG_DEBUG', 'syslog', SysLogHandler.LOG_LOCAL0)

g_logger_1 = mylogger()
g_logger_1.init_logger('CAS', 'LOG_DEBUG', 'syslog', SysLogHandler.LOG_LOCAL1)

g_logger_2 = mylogger()
g_logger_2.init_logger('CAS', 'LOG_DEBUG', 'syslog', SysLogHandler.LOG_LOCAL2)

!CHANGE instance name to a proper one. 
