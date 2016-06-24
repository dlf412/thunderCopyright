#!/usr/bin/python  
import sys  
import time  
from thrift import Thrift  
from thrift.transport import TSocket, TTransport  
from thrift.protocol import TBinaryProtocol  
from hbase import ttypes  
from hbase.Hbase import * 

def create_all_tables(client):  
    '''store table'''  
    table_name = 'store_table'  
    col_name = ['store:']  
    create_table(client, table_name, col_name)  
    table_name2 = 'item_table'  
    col_name2 = ['item:', 'item_page:']  
    create_table(client, table_name2, col_name2)  
def drop_all_tables(client):  
    tables = ['store_table', 'item_table']  
    for table in tables:  
        if client.isTableEnabled(table):  
            print "    disabling table: %s"  %(table)  
            client.disableTable(table)  
        print "    deleting table: %s"  %(table)  
        client.deleteTable(table)  
def create_table(client, table_name, table_desc):  
    columns = []  
    for name in table_desc:  
        col = ColumnDescriptor(name)  
        columns.append(col)  
    try:  
        print "creating table: %s" %(table_name)  
        client.createTable(table_name, columns)  
    except AlreadyExists, ae:  
        print "WARN: " + ae.message  
    except Exception, e:  
        print "error happend: " + str(e)  
def list_all_tables(client):  
    # Scan all tables  
    print "scanning tables..." 
    print "table names:%s"%(client.getTableNames()) 
    #for t in client.getTableNames():  
    #    print "  -- %s" %(t)  
    #    cols = client.getColumnDescriptors(t)  
    #     print "  -- -- column families in %s" %(t)  
    #     for col_name in cols.keys():  
    #        col = cols[col_name]  
    #        print "  -- -- -- column: %s, maxVer: %d" % (col.name, col.maxVersions) 
def getOneRow(client,table,rowKey,colsKey,flag=True):
    result = client.getRow(table, rowKey)
    x_value=None
    #print result
    for r in result:
        if flag:print 'the   row  is: ' , r.row
        x_value=r.columns.get(colsKey).value
        if flag:print 'the  value is: ' , x_value
    return x_value
def getColRow(client,table,rowKey):

    return client.getRow(table, rowKey)

def connect_hbase():  
    # Make socket  
    transport = TSocket.TSocket('182.92.153.94', 9090)  
    # Buffering is critical. Raw sockets are very slow  
    transport = TTransport.TBufferedTransport(transport)  
    # Wrap in a protocol  
    protocol = TBinaryProtocol.TBinaryProtocol(transport)  
    # Create a client to use the protocol encoder  
    client = Client(protocol)  
    # Connect!  
    transport.open()  
    return client  
def printRow(entry):  
    print "row: " + entry.row + ", cols:",  
    for k in sorted(entry.columns):  
        print k + " => " + entry.columns[k].value,  
    print "/n"  

def isMatch(entry,url):
    match_result=False
    for k in sorted(entry.columns):  
        #print k + " => " + entry.columns[k].value
        if entry.columns[k].value.find(url)>0:
           match_result=True
           break
    return match_result

def scann_table(client,table,colsKey):  
    #t = 'sid_tids'
    print 'scan [%s] ...'%(table)
    columnNames = []  
    for (col, desc) in client.getColumnDescriptors(table).items():  
        print "column with name: "+desc.name  
        print desc  
        columnNames.append(desc.name+colsKey)  
    print columnNames  
      
    print "Starting scanner..."  
    scanner = client.scannerOpenWithStop(table, "", "", columnNames)  
      
    r = client.scannerGet(scanner)  
    i = 1  
    while r: 
    	if r != []:
    		print r[0] 
        if i % 100 == 0:  
            printRow(r[0])  
        r = client.scannerGet(scanner) 
        i += 1  
      
    client.scannerClose(scanner)  
    print "Scanner finished, total %d row" % (i-1)  
def getTaskId(client,table,url):
    #t = 'sid_tids'
    print 'scan [%s] ...'%(table)
    columnNames = []  
    for (col, desc) in client.getColumnDescriptors(table).items():  
        print "column with name: "+desc.name  
        print desc  
        columnNames.append(desc.name+"extra_info")  
    print columnNames  
      
    print "Starting scanner..."  
    scanner = client.scannerOpenWithStop(table, "", "", columnNames)  
      
    r = client.scannerGet(scanner) 
    task_id=None 
    i = 1  
    while r: 
    	if r != []:
    		print r[0] 
        if isMatch(r[0],url):
           task_id=r[0].row
           break
        if i % 100 == 0:  
            printRow(r[0])  
        r = client.scannerGet(scanner) 
        i += 1  
      
    client.scannerClose(scanner)  
    return task_id
def main():
    LE=sys.argv
    argc = len (sys.argv);
    if (argc != 2):
        print 'usage: %s json_conf' % sys.argv[0]
        sys.exit (-1)

    print LE[0]
    client = connect_hbase()
    print '\n'
    print "*******************************************"
    #create_all_tables(client)  
    list_all_tables(client)
    print '-----------------------table[sid_tid]-------------------'
    task_id=getOneRow(client,"sid_tid",LE[1],"t:task_uuid",False)
    #source=getOneRow(client,"sid_tid",LE[1],"t:source")
    print "task_id:%s"%(task_id)
    result=getColRow(client,"sid_tid",LE[1])
    print "%s"%(result)
    #print 'task_id:',task_id
    if task_id!=None:
        #task_id=task_id[2:len(task_id)-2]
        print '\n------------------------table[tid_sid]----------------------'
        n=1
        while True:
            result=getOneRow(client,"tid_sid","%s-%d"%(task_id,n),"t:site_asset_id")
            if result==None or n>100:
                break
            n=n+1

        #task record
        print '\n-----------------------table[task]--------------------'
        result=getColRow(client,"task",task_id)
        print "task result:\n%s"%(result)

        print '\n-----------------------table[finished]--------------------'
        result=getColRow(client,"finished",task_id)
        print "finished result:\n%s"%(result)

        print '\n-----------------------table[matches]--------------------'
        n=0
        while True:
            result=getColRow(client,"matches","%s-audio-%s"%(task_id,n))
            result1=getColRow(client,"matches","%s-video-%s"%(task_id,n))
            if result==[] and result1==[]:
                print "matches finished."
                break
            print result
            print result1
            n=n+1

    print "\n*******************************************"
    print '\n'

#def test():
#	client = connect_hbase()
#	taskid=getTaskId(client,"task","http://10.162.207.221/sample/flv1_320x240_mp3.flv")
#	print taskid

if __name__ == '__main__':  
	main()