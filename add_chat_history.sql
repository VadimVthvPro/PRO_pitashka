-- ============================================
-- Создание таблицы для истории чата с ИИ
-- ============================================

\echo 'Создание таблицы chat_history...'

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'bot')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

-- Создаём индекс для быстрого поиска последних сообщений
CREATE INDEX IF NOT EXISTS idx_chat_history_user_created ON chat_history(user_id, created_at DESC);

COMMENT ON TABLE chat_history IS 'История сообщений пользователя с ботом для контекстного общения с ИИ';
COMMENT ON COLUMN chat_history.message_type IS 'Тип сообщения: user (от пользователя) или bot (от бота)';

\echo '✅ Таблица chat_history создана успешно!'

