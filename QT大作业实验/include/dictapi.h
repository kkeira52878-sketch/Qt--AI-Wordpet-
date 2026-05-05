#ifndef DICTAPI_H
#define DICTAPI_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QMap>
#include <QVariant>

class DictApi : public QObject
{
    Q_OBJECT

public:
    explicit DictApi(QObject *parent = nullptr);
    ~DictApi() override;

    void query(const QString& word);

    QString getCachedPhonetic(const QString& word);
    QString getCachedDefinition(const QString& word);

signals:
    void queryFinished(const QString& word, const QString& phonetic,
                      const QString& definition, const QString& example);
    void queryFailed(const QString& word, const QString& error);

private slots:
    void onReplyFinished();

private:
    QString parseResponse(const QByteArray& data);

private:
    QNetworkAccessManager *m_networkManager;
    QMap<QString, QVariantMap> m_cache;  // word -> {phonetic, definition, example}
};

#endif // DICTAPI_H