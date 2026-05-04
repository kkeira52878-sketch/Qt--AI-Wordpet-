#ifndef CLIPBOARDMONITOR_H
#define CLIPBOARDMONITOR_H

#include <QObject>
#include <QTimer>
#include <QString>

class ClipboardMonitor : public QObject
{
    Q_OBJECT

public:
    explicit ClipboardMonitor(QObject *parent = nullptr);
    ~ClipboardMonitor() override;

    void startMonitoring();
    void stopMonitoring();
    bool isMonitoring() const;

signals:
    void wordFound(const QString& word);

private slots:
    void checkClipboard();

private:
    bool isValidEnglishWord(const QString& text);

private:
    QTimer *m_timer;
    QString m_lastContent;
    bool m_enabled;
};

#endif // CLIPBOARDMONITOR_H