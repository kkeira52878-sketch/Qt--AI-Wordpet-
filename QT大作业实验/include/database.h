#ifndef DATABASE_H
#define DATABASE_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QDateTime>
#include <QVariantMap>

struct WordInfo {
    int id;
    QString word;
    QString phonetic;
    QString definition;
    QString example;
    int mastery;          // 0-5
    bool is_favorite;
    QDateTime created_at;
    QDateTime last_reviewed;
    QDateTime next_review;
};

class Database : public QObject
{
    Q_OBJECT

public:
    static Database& instance();

    bool init();
    bool addWord(const QString& word, const QString& phonetic,
                 const QString& definition, const QString& example);
    QVector<WordInfo> getAllWords();
    QVector<WordInfo> searchWords(const QString& keyword);
    bool updateWord(int id, const QString& definition);
    bool deleteWord(int id);
    bool toggleFavorite(int id);
    QVector<WordInfo> getWordsForReview();
    bool updateReviewResult(int word_id, int result);

    // Settings
    QString getSetting(const QString& key, const QString& defaultValue = QString());
    bool setSetting(const QString& key, const QString& value);

private:
    explicit Database(QObject *parent = nullptr);
    ~Database();
    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;

    bool createTables();
    WordInfo wordFromQuery(const QVariantMap& row);

private:
    QString m_dbPath;
};

#endif // DATABASE_H