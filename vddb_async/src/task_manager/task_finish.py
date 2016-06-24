'''
TaskTerminator.

Created on Aug 28, 2013

@author: hpp
'''
from xml.etree import ElementTree


class TaskTerminator(object):
    '''
    to finish the tasks
    '''

    def __init__(self):
        '''
        Constructor
        '''
        pass

    def sync_crr_with_match_list(self, notifications, uuids):
        try:
            root = ElementTree.fromstring(notifications)
        except Exception as e:
            return None

        for n in root:
            ast = n.find('Asset')
            if ast == None:
                continue
            oastid = ast.find('OriginalAssetID')
            if oastid == None:
                continue
            uuid = oastid.text
            if uuid in uuids:
                continue

            root.remove(n)

        result = '<?xml version="1.0" encoding="utf-8" ?>\n\n' + \
                 ElementTree.tostring(root)
        return result[0:65534]
