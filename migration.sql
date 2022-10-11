-- Migration SQL script to transform the old Telegram-only database format to the new schema.
-- Do not use it directly, but rather use it as a template and replace the placeholder variables,
-- e.g. the database names ('original' is the source, 'core' is the core, 'telegram' is the bot).
-- It's expected that all databases and tables already exist and that a community user has been added.
-- Furthermore, the migration of the core MUST has been completed already.

BEGIN;

-- The 'first_name' column will not contain correct data afterwards, but the bot should update those entries anyways.
INSERT INTO telegram_users (telegram_id,user_id,first_name,username,created)
SELECT old_users.tid,new_users.id,old_users.name,old_users.username,old_users.created
FROM original.users AS old_users
    JOIN core.users AS new_users
        ON new_users.name = old_users.username
WHERE old_users.tid IS NOT NULL;

INSERT INTO shared_messages (share_type,share_id,chat_id,message_id)
SELECT 'communism',new_comms.id,old_msgs.chat_id,old_msgs.msg_id
FROM original.collective_messages AS old_msgs
    JOIN original.collectives AS old_colls
        ON old_colls.id = old_msgs.collectives_id
    JOIN core.communisms AS new_comms
        ON new_comms.created = old_colls.created AND new_comms.amount = old_colls.amount AND new_comms.description = old_colls.description AND new_comms.active = TRUE
WHERE old_colls.communistic = 1;

INSERT INTO shared_messages (share_type,share_id,chat_id,message_id)
SELECT 'refund',new_refunds.id,old_msgs.chat_id,old_msgs.msg_id
FROM original.collective_messages AS old_msgs
    JOIN original.collectives AS old_colls
        ON old_colls.id = old_msgs.collectives_id
    JOIN core.refunds AS new_refunds
        ON new_refunds.created = old_colls.created AND new_refunds.amount = old_colls.amount AND new_refunds.description = old_colls.description AND new_refunds.active = TRUE
WHERE old_colls.communistic = 0;

COMMIT;
