#include "database.h"
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSqlRecord>
#include <QVariant>
#include <QDir>
#include <QFile>
#include <QMessageBox>

Database& Database::instance()
{
    static Database instance;
    return instance;
}

Database::Database(QObject *parent)
    : QObject(parent)
    , m_dbPath(QDir::currentPath() + "/data/wordpet.db")
{
}

Database::~Database() = default;

bool Database::init()
{
    // Ensure data directory exists
    QDir dir(QDir::currentPath() + "/data");
    if (!dir.exists()) {
        dir.mkpath(".");
    }

    // Open SQLite database
    QSqlDatabase db = QSqlDatabase::addDatabase("QSQLITE");
    db.setDatabaseName(m_dbPath);

    if (!db.open()) {
        QMessageBox::critical(nullptr, "数据库错误", "无法打开数据库: " + db.lastError().text());
        return false;
    }

    return createTables();
}

bool Database::createTables()
{
    QSqlQuery query;

    // Words table
    if (!query.exec("CREATE TABLE IF NOT EXISTS words ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "word TEXT NOT NULL UNIQUE,"
        "phonetic TEXT DEFAULT '',"
        "definition TEXT DEFAULT '',"
        "example TEXT DEFAULT '',"
        "mastery INTEGER DEFAULT 0,"
        "is_favorite INTEGER DEFAULT 0,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "last_reviewed DATETIME,"
        "next_review DATETIME"
    ")")) {
        return false;
    }

    // Review history table
    if (!query.exec("CREATE TABLE IF NOT EXISTS review_history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "word_id INTEGER NOT NULL,"
        "reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "result INTEGER DEFAULT 0,"
        "FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE"
    ")")) {
        return false;
    }

    // Settings table
    if (!query.exec("CREATE TABLE IF NOT EXISTS settings ("
        "key TEXT PRIMARY KEY,"
        "value TEXT"
    ")")) {
        return false;
    }

    // Create indexes
    query.exec("CREATE INDEX IF NOT EXISTS idx_words_word ON words(word)");
    query.exec("CREATE INDEX IF NOT EXISTS idx_words_next_review ON words(next_review)");

    return true;
}

bool Database::addWord(const QString& word, const QString& phonetic,
                      const QString& definition, const QString& example)
{
    QSqlQuery query;
    query.prepare("INSERT OR IGNORE INTO words (word, phonetic, definition, example) "
                  "VALUES (?, ?, ?, ?)");
    query.bindValue(0, word.toLower().trimmed());
    query.bindValue(1, phonetic);
    query.bindValue(2, definition);
    query.bindValue(3, example);

    return query.exec();
}

QVector<WordInfo> Database::getAllWords()
{
    QVector<WordInfo> words;
    QSqlQuery query("SELECT * FROM words ORDER BY created_at DESC");

    while (query.next()) {
        words.append(wordFromQuery(query.record().toMap()));
    }

    return words;
}

QVector<WordInfo> Database::searchWords(const QString& keyword)
{
    QVector<WordInfo> words;
    QSqlQuery query;
    query.prepare("SELECT * FROM words WHERE word LIKE ? OR definition LIKE ? ORDER BY created_at DESC");
    query.bindValue(0, "%" + keyword + "%");
    query.bindValue(1, "%" + keyword + "%");

    if (query.exec()) {
        while (query.next()) {
            words.append(wordFromQuery(query.record().toMap()));
        }
    }

    return words;
}

bool Database::updateWord(int id, const QString& definition)
{
    QSqlQuery query;
    query.prepare("UPDATE words SET definition = ? WHERE id = ?");
    query.bindValue(0, definition);
    query.bindValue(1, id);
    return query.exec();
}

bool Database::deleteWord(int id)
{
    QSqlQuery query;
    query.prepare("DELETE FROM words WHERE id = ?");
    query.bindValue(0, id);
    return query.exec();
}

bool Database::toggleFavorite(int id)
{
    QSqlQuery query;
    query.prepare("UPDATE words SET is_favorite = NOT is_favorite WHERE id = ?");
    query.bindValue(0, id);
    return query.exec();
}

QVector<WordInfo> Database::getWordsForReview()
{
    QVector<WordInfo> words;
    QSqlQuery query;
    query.prepare("SELECT * FROM words WHERE next_review IS NULL OR next_review <= datetime('now') ORDER BY next_review ASC LIMIT 20");

    if (query.exec()) {
        while (query.next()) {
            words.append(wordFromQuery(query.record().toMap()));
        }
    }

    return words;
}

bool Database::updateReviewResult(int word_id, int result)
{
    // result: 0=忘了, 1=模糊, 2=记住
    QSqlQuery query;

    // Update mastery level (0-5 scale)
    query.prepare("UPDATE words SET mastery = ?, last_reviewed = datetime('now') WHERE id = ?");
    int currentMastery = 0;

    // Get current mastery
    QSqlQuery getQuery;
    getQuery.prepare("SELECT mastery FROM words WHERE id = ?");
    getQuery.bindValue(0, word_id);
    if (getQuery.exec() && getQuery.next()) {
        currentMastery = getQuery.value(0).toInt();
    }

    // Adjust mastery based on result
    int newMastery = currentMastery;
    switch (result) {
        case 0: newMastery = qMax(0, currentMastery - 2); break;  // Forgot - reset
        case 1: newMastery = qMax(0, currentMastery - 1); break;  // Fuzzy - slightly reset
        case 2: newMastery = qMin(5, currentMastery + 1); break;   // Remembered - increase
    }

    query.bindValue(0, newMastery);
    query.bindValue(1, word_id);

    if (!query.exec()) return false;

    // Calculate next review time using spaced repetition
    // Interval = 1 day * 2^mastery
    int daysToReview = qPow(2, newMastery).toInt();
    QSqlQuery updateNextReview;
    updateNextReview.prepare("UPDATE words SET next_review = datetime('now', '+" + QString::number(daysToReview) + " days') WHERE id = ?");
    updateNextReview.bindValue(0, word_id);

    return updateNextReview.exec();
}

QString Database::getSetting(const QString& key, const QString& defaultValue)
{
    QSqlQuery query;
    query.prepare("SELECT value FROM settings WHERE key = ?");
    query.bindValue(0, key);

    if (query.exec() && query.next()) {
        return query.value(0).toString();
    }
    return defaultValue;
}

bool Database::setSetting(const QString& key, const QString& value)
{
    QSqlQuery query;
    query.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)");
    query.bindValue(0, key);
    query.bindValue(1, value);
    return query.exec();
}

WordInfo Database::wordFromQuery(const QVariantMap& row)
{
    WordInfo info;
    info.id = row.value("id").toInt();
    info.word = row.value("word").toString();
    info.phonetic = row.value("phonetic").toString();
    info.definition = row.value("definition").toString();
    info.example = row.value("example").toString();
    info.mastery = row.value("mastery").toInt();
    info.is_favorite = row.value("is_favorite").toBool();
    info.created_at = QDateTime::fromString(row.value("created_at").toString(), Qt::ISODate);
    info.last_reviewed = QDateTime::fromString(row.value("last_reviewed").toString(), Qt::ISODate);
    info.next_review = QDateTime::fromString(row.value("next_review").toString(), Qt::ISODate);
    return info;
}