#include "dictapi.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QUrl>

DictApi::DictApi(QObject *parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
{
}

DictApi::~DictApi() = default;

void DictApi::query(const QString& word)
{
    QString lowerWord = word.toLower().trimmed();

    // Check cache first
    if (m_cache.contains(lowerWord)) {
        QVariantMap cached = m_cache.value(lowerWord);
        emit queryFinished(lowerWord,
                          cached.value("phonetic").toString(),
                          cached.value("definition").toString(),
                          cached.value("example").toString());
        return;
    }

    // Make API request
    QString url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + QUrl::toPercentEncoding(lowerWord);
    QNetworkRequest request(QUrl(url));
    request.setHeader(QNetworkRequest::UserAgentHeader, "WordPet/1.0");

    QNetworkReply *reply = m_networkManager->get(request);
    connect(reply, &QNetworkReply::finished, this, &DictApi::onReplyFinished);
}

void DictApi::onReplyFinished()
{
    QNetworkReply *reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    QString url = reply->url().toString();
    QString word = url.split("/").last();  // Extract word from URL

    if (reply->error() == QNetworkReply::NoError) {
        QByteArray data = reply->readAll();
        QString result = parseResponse(data);

        if (!result.isEmpty()) {
            emit queryFinished(word, "", result, "");
            return;
        }
    }

    emit queryFailed(word, reply->errorString());
    reply->deleteLater();
}

QString DictApi::parseResponse(const QByteArray& data)
{
    QJsonDocument doc = QJsonDocument::fromJson(data);
    if (!doc.isArray()) return QString();

    QJsonArray array = doc.array();
    if (array.isEmpty()) return QString();

    // Get first entry
    QJsonObject entry = array[0].toObject();
    QString word = entry.value("word").toString();
    QString phonetic = entry.value("phonetic").toString();

    // Get meanings
    QJsonArray meanings = entry.value("meanings").toArray();
    QStringList definitions;

    for (const QJsonValue& meaning : meanings) {
        QString partOfSpeech = meaning.toObject().value("partOfSpeech").toString();
        QJsonArray defs = meaning.toObject().value("definitions").toArray();

        for (int i = 0; i < qMin(3, defs.size()); ++i) {
            QString def = defs[i].toObject().value("definition").toString();
            definitions.append(QString("[%1] %2").arg(partOfSpeech, def));
        }
    }

    // Cache the result
    QVariantMap cached;
    cached.insert("phonetic", phonetic);
    cached.insert("definition", definitions.join("\n"));
    m_cache.insert(word.toLower(), cached);

    return definitions.join("\n");
}

QString DictApi::getCachedPhonetic(const QString& word)
{
    if (m_cache.contains(word.toLower())) {
        return m_cache.value(word.toLower()).value("phonetic").toString();
    }
    return QString();
}

QString DictApi::getCachedDefinition(const QString& word)
{
    if (m_cache.contains(word.toLower())) {
        return m_cache.value(word.toLower()).value("definition").toString();
    }
    return QString();
}