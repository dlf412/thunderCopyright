# utils
USURP = '''UPDATE masterProcess
              SET host = %s, port = %s, heartbeat_time = NOW()
            WHERE module_name = %s
              AND ((host = %s AND port = %s)
                   OR (heartbeat_time < NOW() - INTERVAL %s SECOND))'''
CHECK_THRONE = '''SELECT id FROM masterProcess WHERE module_name = %s'''
MAKE_THRONE = '''INSERT INTO masterProcess(module_name, host, port,
                                           heartbeat_time)
                      VALUES (%s, %s, %s, NOW())'''
# loader
LOAD_ACCOUNTS = '''SELECT c.id AS id, max_query_thread_num AS max_conc,
                          min_query_thread_num AS min_conc,
                          max_pending_queue_size AS max_buf,
                          min_pending_queue_size AS min_buf,
                          max_process_time AS time_limit,
                          u1.username AS backend_user,
                          u1.password AS backend_pass,
                          u2.username AS hot_user, u2.password AS hot_pass,
                          u1.is_delete AS user_deleted,
                          u2.is_delete AS hot_user_deleted,
                          is_slice_query AS slicing, slice_duration,
                          is_hot_query AS hot, is_requery as do_reverse,
                          company_domain AS domain, c.is_retry AS retry,
                          'true' AS allow_partial
                     FROM company AS c
                     JOIN vddbUser AS u1
                       ON c.vddbUser_id = u1.id
                LEFT JOIN vddbUser AS u2
                       ON c.hot_vddbUser_id = u2.id
                    WHERE c.is_delete = "false"'''
ACCOUNT_BACKENDS = '''SELECT company_id AS account, vddbNode_id AS backend,
                             query_level AS level, query_mode AS mode,
                             extra_option AS extra
                        FROM vddbNode_company v, company AS c
                       WHERE c.id = company_id
                         AND c.is_delete = "false"'''
LOAD_RULES = '''SELECT company_id AS account, key_name AS k, value
                  FROM companyResultRule AS r, company AS c
                 WHERE c.id = company_id AND c.is_delete = "false"'''
LOAD_BACKENDS = '''SELECT id, max_connection AS capacity, vddb_address
                     FROM vddbNode'''
# fetcher
RENEW_TASKS = '''UPDATE task SET status = 'new'
                  WHERE status NOT IN ('new', 'query_failed', 'query_success')'''
FETCH_TASKS = '''SELECT id, task_identification AS uuid,
                        task_priority AS priority, queued_at,
                        external_id,
                        query_count AS retries, site_asset_id,
                        clip_format AS format,
                        dna_url as dna_url,
                        company_id AS account,
                        UNIX_TIMESTAMP(deadline) AS deadline,
                        UNIX_TIMESTAMP(submitted_at) AS submit_at,
                        UNIX_TIMESTAMP(created_at) AS created_at,
                        is_requery AS from_reverse
                   FROM task
                  WHERE company_id = %s AND status = 'new'
               ORDER BY task_priority DESC, queued_at ASC
                  LIMIT %s'''

LOAD_TASK_STATUS = '''SELECT task_identification AS uuid,
                        queued_at, query_count, status,
                        task_result, start_query_time, end_query_time,
                        billing_time, error_code,
                        site_asset_id, external_id,
                        company_id, task_priority, user_id, clip_duration,
                        clip_format, clip_url, dna_type, query_level,
                        is_indexed, is_requery, result_revision,
                        userClientInfo_id, created_at, compressed_file_size,
                        processed_file_size, deadline, dna_url
                   FROM task
                  WHERE task_identification = %s '''

FETCH_SCOPE = '''SELECT m.meta_uuid AS content
                   FROM task_vddbMetaContent AS r
                   JOIN vddbMetaContent AS m
                     ON r.vddbMetaContent_id = m.id
                  WHERE r.task_id = %s'''
# manager
BEGIN_QUERY = '''UPDATE task
                   SET status = 'query', task_pid = %s, start_query_time = NOW()
                 WHERE id = %s AND status = "new"'''
QUERY_EVENT = '''INSERT INTO taskQueryHis(task_identification, task_pid,
                                          created_at)
                      VALUES (%s, %s, NOW())'''
# cleaner
RETRY_TASK = '''UPDATE task
                   SET status = 'new', queued_at = from_unixtime(%s), error_code = %s,
                       query_count = query_count + 1, end_query_time = NOW(),
                       fetch_time = 0, task_result = 'no_match'
                 WHERE id = %s AND status IN ('query_failed', 'query')'''
RENEW_EVENT = '''INSERT INTO taskRenewHis(task_identification, reason,
                                          created_at)
                      VALUES (%s, %s, NOW())'''
CHECK_TASK = '''SELECT 1 AS yes
                  FROM task
                 WHERE id = %s AND status = "query_success"'''
FAIL_TASK = '''UPDATE task
                  SET status = 'query_failed', error_code = %s,
                      query_count = query_count + 1, end_query_time = NOW(),
                      fetch_time = 0, task_result = 'no_match'
                WHERE id = %s AND status != "query_success"'''
UPDATE_QUERY = '''UPDATE taskQueryHis
                     SET task_identification = %s, finished_at = NOW(),
                         error_code = %s, match_count = %s
                   WHERE id = %s'''
FATAL_QUERY = '''INSERT INTO taskQueryHis(task_identification, error_code,
                                          created_at, finished_at)
                      VALUES (%s, %s, NOW(), NOW())'''
FINISH_TASK = '''UPDATE task
                    SET task_result = %s, error_code = %s, fetch_time = 0,
                        end_query_time = NOW(), status = 'query_success',
                        result_revision = result_revision + 1,
                        query_count = query_count + 1,
                        billing_time = IFNULL(billing_time, NOW())
                  WHERE id = %s'''
STORE_CRR = '''INSERT INTO contentRecognitionRul(task_identification, crr,
                                                 created_at)
                    VALUES (%s, %s, NOW())
   ON DUPLICATE KEY UPDATE crr = %s'''
STORE_MATCH = '''INSERT INTO matchVideo(company_id, meta_uuid,
                                        task_identification, task_created_at,
                                        site_asset_id, media_type,
                                        video_duration, video_score,
                                        video_sample_offset,
                                        video_master_offset, audio_duration,
                                        audio_score, audio_sample_offset,
                                        audio_master_offset, created_at,
                                        match_type, clip_duration)
                      VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, NOW(), %s, %s)
     ON DUPLICATE KEY UPDATE company_id = %s, media_type = %s,
                             video_duration = %s, video_score = %s,
                             video_sample_offset = %s, video_master_offset = %s,
                             audio_duration = %s, audio_score = %s,
                             audio_sample_offset = %s, audio_master_offset = %s,
                             match_type = %s, clip_duration = %s'''
ADD_CONTENT = '''INSERT IGNORE INTO vddbMetaContent(meta_uuid, meta_title)
                             VALUES (%s, %s)'''
CHECK_MATCHES = '''SELECT COUNT(*) AS count
                     FROM matchVideo
                    WHERE task_identification = %s
                      AND match_type IN ('auto_match', 'manual_match', 'no_crr',
                                         'uncertain')'''
