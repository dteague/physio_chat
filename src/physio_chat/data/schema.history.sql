CREATE TABLE chats (
    id integer PRIMARY KEY,
    timestamp text DEFAULT CURRENT_TIME,
    patient_profile text NON NULL
);

CREATE TABLE histories (
    id integer PRIMARY KEY,
    chat_id integer NONE NULL,
    query text NONE NULL,
    response text NONE NULL,
    FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE facts (
    id integer PRIMARY KEY,
    history_id integer NONE NULL,
    chunk_id integer NONE NULL,
    FOREIGN KEY(history_id) REFERENCES histories(id) ON DELETE CASCADE
);
