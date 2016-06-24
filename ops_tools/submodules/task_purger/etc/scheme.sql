
-- 被删除消息存储的表
DROP TABLE IF EXISTS purged_task;
CREATE TABLE purged_task (
       id               int unsigned NOT NULL AUTO_INCREMENT,
       custom_type      CHAR(32) NOT NULL,
       client_id        CHAR(150) CHARACTER SET utf8  NOT NULL,
       file_private_id  CHAR(150) DEFAULT '',
       url              VARCHAR(1024) CHARACTER SET utf8 NOT NULL,
       digest           CHAR(150) NOT NULL,
       algorithm        CHAR(32) DEFAULT '' comment 'digest algorithm', 
       mime_type        CHAR(64) DEFAULT '',
       file_name        VARCHAR(512) CHARACTER SET utf8 DEFAULT '',
       file_size        INT DEFAULT -1,
       swift_path       CHAR(200) DEFAULT '' comment 'torrent path in swift', 
       created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
       primary key(id),
       UNIQUE KEY uk_digest_algorithm(digest,algorithm)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='Purged tasks';

