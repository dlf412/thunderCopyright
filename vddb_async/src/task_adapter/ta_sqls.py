# task_adapter

STORE_TASK = '''INSERT INTO task(task_identification, external_id, task_priority, created_at
                                , dna_url, company_id, clip_format,
                                site_asset_id)
                VALUES (%s, %s, %s, %s, %s, %s, 'dna', %s)'''

UPDATE_TASK_STATUS = ''' UPDATE task SET status='new',
                        site_asset_id=%s,external_id=%s where
                        task_identification=%s and status!='query'
                     '''

GEN_UUID = ''' SELECT uuid() as uuid '''

GET_PRIORITY = '''SELECT task_priority FROM company WHERE id = %s '''

GET_COMPANYID = ''' SELECT company_id FROM user WHERE id = %s '''

STORE_SCOPE = ''' INSERT INTO task_vddbMetaContent SET task_id=(SELECT id FROM
                    task WHERE task_identification =%s),
                    vddbMetaContent_id=(SELECT id FROM vddbMetaContent where
                    meta_uuid = %s)'''

CHECK_SCOPE = '''SELECT * FROM vddbMetaContent where meta_uuid=%s '''
